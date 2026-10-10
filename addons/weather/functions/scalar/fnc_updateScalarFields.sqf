#include "..\..\script_component.hpp"
#include "\z\aee\addons\lib\script_debug.hpp"

/*
Scalar-field transport driver (issue #116).

One tick of the unified advection engine.  It owns the engine state (the
grids and the source registry), calls the pure kernels, and publishes the
result.  Every field in FUNC(scalarFieldConfig) is stepped the same way:

  1. inject the tick's sources (emitter cells, or a wind-gated background),
  2. advect one step with the semi-Lagrangian kernel, driven by the repo's
     own wind field EGVAR(core,currentWind),
  3. apply the sinks (rain scavenging + dry-deposition decay),
  4. publish the grid, a summary, and the cells above the visibility
     threshold.

The grid is the issue's recommended 2D grid: 31x31 cells at 1 km, one flat
row-major array per field, index i + j * 31.  The origin is the world centre
minus half the span, so the grid is identical on every machine (the field is
local state; nothing is broadcast).

This is the single advection core the issue asks for.  The point-scalar
models it replaces stay as INPUTS, not as parallel models: the dust source
reads the repo's own dust suppression, and the smoke sink reuses the repo's
own rain-scavenging factor (see FUNC(scalarFieldConfig) for the citations).

Runs on the core environment tick, gated by GVAR(scalarFieldsEnabled).
*/

if (!GVAR(scalarFieldsEnabled)) exitWith {};

private _dt = missionNamespace getVariable [QEGVAR(core,updateInterval), 5];
if !(_dt isEqualType 0) then { _dt = 5; };
_dt = _dt max 1;

// ─── Grid geometry (the issue's recommended 2D grid) ──────────────────────
private _gridW = 31;
private _gridH = 31;
private _cellM = 1000;
// Surface-layer depth for the dry-removal time constant tau = H / v_d.  A
// STATED modelling depth, not a measured constant (UNSOURCED).
private _layerDepthM = 100;

private _halfSpan = (_gridW * _cellM) / 2;
private _originX = (worldSize / 2) - _halfSpan;
private _originY = (worldSize / 2) - _halfSpan;
private _cellCount = _gridW * _gridH;

// ─── Inputs (the repo's own state) ────────────────────────────────────────
private _wind = missionNamespace getVariable [QEGVAR(core,currentWind), [0, 0]];
private _u = _wind select 0;
private _v = _wind select 1;
private _windSpeed = vectorMagnitude _wind;
private _rain = rain;
if (isNil "_rain") then { _rain = 0; };
private _suppression = missionNamespace getVariable [QEGVAR(core,dustSuppression), 1];
if !(_suppression isEqualType 0) then { _suppression = 1; };
_suppression = _suppression max 0 min 1;

// ─── Stability diagnostic (cited CFL and von Neumann numbers) ─────────────
private _stab = [_u, _v, _cellM, _dt, 0] call FUNC(scalarStabilityKernel);
missionNamespace setVariable [QGVAR(scalarCflAdvection), _stab select 0];
missionNamespace setVariable [QGVAR(scalarDiffusionNumber), _stab select 1];
missionNamespace setVariable [QGVAR(scalarStable), _stab select 2];

private _store = missionNamespace getVariable [QGVAR(scalarFields), createHashMap];
private _meta = missionNamespace getVariable [QGVAR(scalarGridMeta), createHashMap];
private _sources = missionNamespace getVariable [QGVAR(scalarSources), []];
private _summary = createHashMap;
private _now = diag_tickTime;
// Previous tick's published summary.  A field that carries no mass and has no
// source is a fixed point of the transport, so its published total (index 1)
// is the cheap emptiness test that gates the O(cells) passes below.
private _prevSummary = missionNamespace getVariable [QGVAR(scalarSummary), createHashMap];
// The descriptor table is a constant.  Read it once, not once per loop below.
private _config = call FUNC(scalarFieldConfig);

{
    _x params ["_key", "_vd", "_kScav", "_sourceMode", "_windThresh", "_hotFraction"];

    // ─── Empty-field gate ─────────────────────────────────────────────────
    // Advecting, scavenging and reporting an all-zero field is an exact
    // no-op: zeros advect to zeros, the sink multiplies by a constant, and
    // the summary is [0, 0, [0, 0], 0].  A field gains mass only through a
    // live registry emitter or the wind-gated background source.  When the
    // field holds no mass and nothing feeds it this tick, skip the four
    // O(cells) passes and republish the empty summary.  Emptiness is read
    // from the previous tick's published total, so no grid scan is needed.
    private _prevTotal = (_prevSummary getOrDefault [_key, []]) param [1, 0];
    if !(_prevTotal isEqualType 0) then { _prevTotal = 0; };
    private _fed = if (_sourceMode isEqualTo "registry") then {
        private _has = false;
        {
            if (((_x select 0) == _key) && ((_x select 5) >= _now)) exitWith { _has = true; };
        } forEach _sources;
        _has
    } else {
        ((((_windSpeed - _windThresh) / 15) min 1) max 0) > 0
    };
    if (!_fed && {_prevTotal <= 1e-9}) then {
        _summary set [_key, [0, 0, [0, 0], 0]];
        missionNamespace setVariable [format [QGVAR(scalarHotCells_%1), _key], []];
        missionNamespace setVariable [format [QGVAR(scalarMax_%1), _key], 0];
        continue;
    };

    // ─── Grid (get, or initialise to zero) ────────────────────────────────
    private _grid = _store getOrDefault [_key, []];
    if ((count _grid) != _cellCount) then {
        _grid = [];
        _grid resize _cellCount;
        for "_k" from 0 to (_cellCount - 1) do { _grid set [_k, 0]; };
    };

    // ─── Sources ──────────────────────────────────────────────────────────
    if (_sourceMode isEqualTo "registry") then {
        {
            _x params ["_sKey", "_sx", "_sy", "_strength", "_radius", "_expiry"];
            if ((_sKey == _key) && (_expiry >= _now)) then {
                private _ci = floor ((_sx - _originX) / _cellM);
                private _cj = floor ((_sy - _originY) / _cellM);
                private _rCells = ceil ((_radius max 1) / _cellM);
                for "_dj" from (-_rCells) to _rCells do {
                    for "_di" from (-_rCells) to _rCells do {
                        private _i = _ci + _di;
                        private _j = _cj + _dj;
                        if ((_i >= 0) && (_j >= 0) && (_i < _gridW) && (_j < _gridH)) then {
                            private _dx = (_originX + _i * _cellM) - _sx;
                            private _dy = (_originY + _j * _cellM) - _sy;
                            private _dist = sqrt (_dx * _dx + _dy * _dy);
                            if (_dist <= _radius) then {
                                private _idx = _i + _j * _gridW;
                                private _w = 1 - (_dist / (_radius max 1));
                                _grid set [_idx, (_grid select _idx) + _strength * _w];
                            };
                        };
                    };
                };
            };
        } forEach _sources;
    } else {
        // Background source (dust): a wind-gated uniform surface emission.
        // windFactor reuses the repo's atmospheric-dust gate, (wind - 5) / 15
        // clamped to [0, 1] (fnc_particleEmission.sqf).
        private _windFactor = (((_windSpeed - _windThresh) / 15) min 1) max 0;
        if (_windFactor > 0) then {
            private _add = _windFactor * _suppression * _dt;
            for "_k" from 0 to (_cellCount - 1) do {
                _grid set [_k, (_grid select _k) + _add];
            };
        };
    };

    // ─── Advect (semi-Lagrangian, the pure kernel) ────────────────────────
    _grid = [_grid, _gridW, _gridH, _originX, _originY, _cellM, _u, _v, _dt]
        call FUNC(scalarAdvectKernel);

    // ─── Sinks: rain scavenging + dry-deposition decay ────────────────────
    private _scavenge = 1 / (1 + _rain * _kScav);
    private _tau = _layerDepthM / (_vd max 1e-6);
    private _sink = _scavenge * (exp (-_dt / _tau));
    if (_sink < 1) then {
        for "_k" from 0 to (_cellCount - 1) do {
            _grid set [_k, (_grid select _k) * _sink];
        };
    };

    _store set [_key, _grid];

    // ─── Summary and the cells above the visibility threshold ─────────────
    private _max = 0;
    private _sum = 0;
    private _wx = 0;
    private _wy = 0;
    for "_j" from 0 to (_gridH - 1) do {
        for "_i" from 0 to (_gridW - 1) do {
            private _c = _grid select (_i + _j * _gridW);
            _sum = _sum + _c;
            if (_c > _max) then { _max = _c; };
            _wx = _wx + _c * (_originX + _i * _cellM);
            _wy = _wy + _c * (_originY + _j * _cellM);
        };
    };
    private _centroid = if (_sum > 1e-6) then { [_wx / _sum, _wy / _sum] } else { [0, 0] };
    private _hotThresh = _max * _hotFraction;
    private _hot = [];
    if (_hotThresh > 0) then {
        for "_j" from 0 to (_gridH - 1) do {
            for "_i" from 0 to (_gridW - 1) do {
                if ((_grid select (_i + _j * _gridW)) >= _hotThresh) then {
                    _hot pushBack [_originX + _i * _cellM, _originY + _j * _cellM];
                };
            };
        };
    };
    _summary set [_key, [_max, _sum, _centroid, count _hot]];
    missionNamespace setVariable [format [QGVAR(scalarHotCells_%1), _key], _hot];
    missionNamespace setVariable [format [QGVAR(scalarMax_%1), _key], _max];
} forEach _config;

missionNamespace setVariable [QGVAR(scalarFields), _store];
missionNamespace setVariable [QGVAR(scalarSummary), _summary];
missionNamespace setVariable [QGVAR(scalarGridMeta), _meta];
{
    _meta set [_x select 0, [_gridW, _gridH, _originX, _originY, _cellM]];
} forEach _config;

// ─── Prune expired sources ────────────────────────────────────────────────
private _live = [];
{ if ((_x select 5) >= _now) then { _live pushBack _x }; } forEach _sources;
missionNamespace setVariable [QGVAR(scalarSources), _live];
