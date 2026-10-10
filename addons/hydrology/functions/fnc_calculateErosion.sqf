#include "..\script_component.hpp"
/*
Erosion and sediment transport driver (RUSLE, issue #21).

Computes the RUSLE soil loss at the current position from the mod's own
state, and publishes it. This is the minimal, honest model the issue asks
for: a per-cell closed-form product that REUSES the existing physics.

Reused, not rebuilt:
  - slope length lambda from the D8 flow accumulation
    (fnc_routeRunoffD8), the same catchment the river stage uses;
  - the storm depth and cumulative runoff the river chain already tracks
    (GVAR(stormDepth_mm), GVAR(runoffCumulative_mm));
  - the surface material from the material classifier, mapped to a USDA
    texture with the same associations the Green-Ampt infiltration uses;
  - the seasonal vegetation density the biome model publishes.

The factors:
  R  event erosivity, EI30 from the storm energy and the intensity
     (fnc_calculateKineticEnergy, fnc_calculateErosivityIndex);
  K  soil erodibility from the surface texture (fnc_calculateSoilErodibility);
  LS slope length-gradient from the terrain and the flow-accumulation
     length (fnc_calculateSlopeLengthGradient);
  C  cover-management from the surface and the vegetation
     (fnc_calculateCoverFactor);
  P  1.0, wild terrain carries no support practice.

  A = R * K * LS * C * P   (fnc_calculateSoilLoss)
  mm/yr = A / (10 * BD)    (fnc_calculateErosionDepth)

Event sediment yield is the MUSLE (fnc_calculateSedimentYield): the runoff
volume Q and the peak rate qp replace the annual R.

CEILING. The engine cannot lower terrain at the sub-millimetre rates this
model predicts, and scripted terrain deformation (setTerrainHeight, since
2.10) is a separate server-side, cell-rounded, JIP-queued feature. The
reachable effect is therefore the computed RATE: this driver publishes the
soil loss, the lowering, the sediment yield and the break deposition, and
does not deform terrain.

Stored in GVAR(erosionRate_thaYr), GVAR(erosionDepth_mmYr),
GVAR(erosivityR), GVAR(sedimentYield_t), GVAR(erosionRisk),
GVAR(erosionDepositedFraction).
*/

// ─── Position (the fallback the river and pressure kernels use) ───────────
private _unit = call CBA_fnc_currentUnit;
private _pos = [0, 0];
if (!isNil "_unit" && {!isNull _unit}) then {
    _pos = getPos _unit;
};

// ─── Surface material -> USDA texture ─────────────────────────────────────
// The material classifier is the hydrology's own surface source. The
// material-to-texture associations are the ones fnc_calculateGreenAmptInfiltration
// uses, so the erosion and the infiltration read the same soil.
private _surfaceClass = (surfaceType _pos) call EFUNC(material,classifyBySurfaceType);
private _texture = switch (_surfaceClass) do {
    case "rock":       { "clay" };
    case "gravel":     { "sandy loam" };
    case "vegetation": { "silt loam" };
    case "concrete":   { "clay" };
    case "asphalt":    { "clay" };
    case "metal":      { "clay" };
    case "water":      { "silty clay" };
    default            { "loam" };
};

// Water carries no hillslope soil loss. Publish a zero state and stop.
if (_surfaceClass == "water") exitWith {
    missionNamespace setVariable [QGVAR(erosionRate_thaYr), 0];
    missionNamespace setVariable [QGVAR(erosionDepth_mmYr), 0];
    missionNamespace setVariable [QGVAR(erosivityR), 0];
    missionNamespace setVariable [QGVAR(sedimentYield_t), 0];
    missionNamespace setVariable [QGVAR(erosionRisk), 0];
    missionNamespace setVariable [QGVAR(erosionDepositedFraction), 0];
};

// ─── Slope from the heightmap gradient (4 cardinal samples) ───────────────
// The same sampling the fire-spread model uses. The gradient is the drop
// over the sample radius, a rise/run fraction.
private _radius = 50;
private _hC = getTerrainHeightASL _pos;
private _hN = getTerrainHeightASL [_pos#0, (_pos#1) + _radius];
private _hS = getTerrainHeightASL [_pos#0, (_pos#1) - _radius];
private _hE = getTerrainHeightASL [(_pos#0) + _radius, _pos#1];
private _hW = getTerrainHeightASL [(_pos#0) - _radius, _pos#1];

// Signed gradients: positive means the ground falls in that direction.
private _gN = (_hC - _hN) / _radius;
private _gS = (_hC - _hS) / _radius;
private _gE = (_hC - _hE) / _radius;
private _gW = (_hC - _hW) / _radius;

private _slopeFraction = (abs _gN) max (abs _gS) max (abs _gE) max (abs _gW);

// ─── Slope length from the D8 flow accumulation ───────────────────────────
// The contributing area at the cell, divided by the cell width, is the
// horizontal slope length: lambda = A / b (Desmet and Govers 1996; the
// unit-contour-width form). The accumulation is cached by the river chain,
// so this is a hash lookup, not a second heightmap sweep.
private _step = 100;
private _side = (ceil (worldSize / _step)) max 1;
private _area = [[0, 0], _side, _side, _step] call FUNC(routeRunoffD8);
private _ix = (floor ((_pos select 0) / _step)) min (_side - 1) max 0;
private _iy = (floor ((_pos select 1) / _step)) min (_side - 1) max 0;
private _catchmentM2 = _area param [(_iy * _side) + _ix, 0];
if !(_catchmentM2 isEqualType 0) then { _catchmentM2 = 0; };
// Cap the length: the RUSLE slope length is bounded where deposition
// begins, and an uncapped catchment length would run to hundreds of
// metres. 300 m is the practical upper bound (UNSOURCED cap).
private _slopeLength = (_catchmentM2 / _step) max 22.13 min 300;

// ─── Factors ──────────────────────────────────────────────────────────────
private _k = [_texture] call FUNC(calculateSoilErodibility);
private _ls = [_slopeFraction, _slopeLength] call FUNC(calculateSlopeLengthGradient);

// Cover class from the surface and the seasonal vegetation density.
private _foliage = missionNamespace getVariable [QEGVAR(weather,currentFoliageDensity), 0];
if !(_foliage isEqualType 0) then { _foliage = 0; };
private _coverClass = switch (_surfaceClass) do {
    case "vegetation": { ["pasture", "forest"] select (_foliage >= 0.5) };
    case "rock":       { "bare" };
    case "gravel":     { "bare" };
    default            { "bare" };
};
private _c = [_coverClass] call FUNC(calculateCoverFactor);
private _p = 1.0;

// ─── Event erosivity R (EI30) from the storm the river chain tracks ───────
// The engine rain 1.0 is 30 mm/h (the river chain's convention). The storm
// energy is the per-millimetre energy at the current intensity times the
// storm depth; I30 is the current intensity. This treats the storm as if
// it fell at the present intensity, a documented simplification.
private _intensity = rain;
if !(_intensity isEqualType 0) then { _intensity = 0; };
_intensity = (_intensity max 0) * 30;
private _stormDepth = missionNamespace getVariable [QGVAR(stormDepth_mm), 0];
if !(_stormDepth isEqualType 0) then { _stormDepth = 0; };
private _ePerMm = [_intensity] call FUNC(calculateKineticEnergy);
private _stormEnergy = _ePerMm * _stormDepth;
private _r = [_stormEnergy, _intensity] call FUNC(calculateErosivityIndex);

// ─── Soil loss and lowering ───────────────────────────────────────────────
private _a = [_r, _k, _ls, _c, _p] call FUNC(calculateSoilLoss);
private _bulkDensity = 1.3;
private _depth = [_a, _bulkDensity] call FUNC(calculateErosionDepth);

// ─── Event sediment yield (MUSLE) ─────────────────────────────────────────
// Q is the event runoff volume over the cell's catchment, from the
// cumulative runoff depth the river chain tracks. qp is the interval-mean
// rate Q / interval; the true instantaneous peak is higher, so this is a
// conservative lower bound (UNSOURCED peak relation).
private _interval = missionNamespace getVariable [QEGVAR(core,updateInterval), 5];
if !(_interval isEqualType 0) then { _interval = 5; };
_interval = _interval max 1;
private _runoffMm = missionNamespace getVariable [QGVAR(runoffCumulative_mm), 0];
if !(_runoffMm isEqualType 0) then { _runoffMm = 0; };
private _q = (_runoffMm / 1000) * _catchmentM2;
private _qp = _q / _interval;
private _sed = [_q, _qp, _k, _ls, _c, _p] call FUNC(calculateSedimentYield);

// ─── Slope-break deposition ───────────────────────────────────────────────
// The downslope gradient is sampled at twice the radius along the steepest
// descent direction. A break retains a fraction of the load.
private _downslopeGradient = _slopeFraction;
private _maxDown = _gN max _gS max _gE max _gW;
if (_maxDown > 0) then {
    private _dx = 0;
    private _dy = 0;
    if (_maxDown == _gN) then { _dy = 1; };
    if (_maxDown == _gS) then { _dy = -1; };
    if (_maxDown == _gE) then { _dx = 1; };
    if (_maxDown == _gW) then { _dx = -1; };
    private _hFar = getTerrainHeightASL [
        (_pos#0) + (_dx * 2 * _radius),
        (_pos#1) + (_dy * 2 * _radius)
    ];
    _downslopeGradient = abs ((_hC - _hFar) / (2 * _radius));
};
private _deposited = [_slopeFraction, _downslopeGradient] call FUNC(calculateSedimentDeposition);

// ─── Publish ──────────────────────────────────────────────────────────────
// Risk is the soil loss normalised against 50 t/ha/yr, the top of the
// issue's bare-slope band. The 50 reference is UNSOURCED; it is a display
// scale, not a physical threshold.
private _risk = (_a / 50) min 1;

missionNamespace setVariable [QGVAR(erosionRate_thaYr), _a];
missionNamespace setVariable [QGVAR(erosionDepth_mmYr), _depth];
missionNamespace setVariable [QGVAR(erosivityR), _r];
missionNamespace setVariable [QGVAR(sedimentYield_t), _sed];
missionNamespace setVariable [QGVAR(erosionRisk), _risk];
missionNamespace setVariable [QGVAR(erosionDepositedFraction), _deposited];
