#include "..\script_component.hpp"

/*
Avalanche risk index (0-1) from McClung & Schaerer slab physics.

Replaces the 4-factor heuristic (slope/wind/temp/rain sums) with the
shear-stress stability model:

  tau        = rho·g·h·sin(psi)          slab shear stress
  tau_strength = weak-layer strength      (1-10 kPa, snowpack quality)
  S          = tau_strength / tau         stability index
  release    = S < 1 AND trigger present

Release zones cluster at 30-45 deg (Schweizer et al. 2003).  The danger
scale (1-5) maps to expected release frequency: Low ~1/day, Moderate,
Considerable, High, Extreme ~88/day (McClung & Schaerer 2009).

Burial survival: 93% at 15 min, 30% at 35 min, 3% after 90 min;
asphyxia is 75% of deaths.  Published for rescue UX.

Sets:
  QEGVAR(core,currentAvalancheRisk)      — float 0-1 (stability-derived)
  QGVAR(currentAvalancheWarning)   — "None" / "Low" / "Moderate" / "High" / "Extreme"
  QGVAR(currentAvalancheStability) — S index (diagnostic)
*/

params [["_posASL", [], [[]]]];

private _groundState = missionNamespace getVariable [QEGVAR(core,groundState), "Normal"];

// ─── Early exit: no snowpack ────────────────────────────────────────────
if (_groundState != "Snow" && (_groundState != "Frozen")) exitWith {
    missionNamespace setVariable [QEGVAR(core,currentAvalancheRisk),    0];
    missionNamespace setVariable [QGVAR(currentAvalancheWarning), "None"];
    missionNamespace setVariable [QGVAR(currentAvalancheStability), 99];
    0
};

// ─── Position ───────────────────────────────────────────────────────────
private _pos2D = [];
if (_posASL isEqualTo []) then {
    private _player = call CBA_fnc_currentUnit;
    if (!isNil "_player") then { _pos2D = getPos _player; };
} else {
    _pos2D = _posASL select [0, 2];
};

// ─── Slope from 4 cardinal samples at 50 m radius ───────────────────────
private _slopeDeg = 0;
if (_pos2D isNotEqualTo []) then {
    private _c = getTerrainHeightASL _pos2D;
    private _n = getTerrainHeightASL [_pos2D#0, (_pos2D#1) + 50];
    private _s = getTerrainHeightASL [_pos2D#0, (_pos2D#1) - 50];
    private _e = getTerrainHeightASL [(_pos2D#0) + 50, _pos2D#1];
    private _w = getTerrainHeightASL [(_pos2D#0) - 50, _pos2D#1];
    private _maxDiff = (abs (_c - _n)) max (abs (_c - _s)) max (abs (_c - _e)) max (abs (_c - _w));
    _slopeDeg = atan (_maxDiff / 50);
};

// ─── McClung & Schaerer shear-stress stability ──────────────────────────
// Shear stress: tau = rho·g·h·sin(psi).  Slab density 200-400 kg/m3,
// slab depth 0.3-2 m (spec).  Surface-hoar weak layer 1-10 kPa.
private _rho = missionNamespace getVariable [QGVAR(slabDensity), 300];
if !(_rho isEqualType 0) then { _rho = 300; };
private _slabH = missionNamespace getVariable [QGVAR(slabDepth), 1.0];
if !(_slabH isEqualType 0) then { _slabH = 1.0; };

private _psi = _slopeDeg * pi / 180;
private _tau = _rho * 9.81 * _slabH * sin _psi;              // Pa

// Weak-layer strength scales with snowpack quality: cold dry snow is
// strong, warm/rain/wind-weakened snow is weak.
private _temp = EGVAR(core,currentTemperature);
if (isNil "_temp") then { _temp = 0; };
private _quality = 1.0;
if (_temp > 0)  then { _quality = _quality - 0.4; };         // warm weakens
if (rain > 0)   then { _quality = _quality - 0.3; };         // rain lubricates
if (_quality < 0.2) then { _quality = 0.2; };
private _tauStrength = 1 + (_quality * 9);                    // 1-10 kPa

private _S = _tauStrength / (_tau / 1000);                    // kPa / kPa

// ─── Trigger: new snow loading (30 cm in 24 h) or warm-up spike ─────────
// Rolling 24 h window: maintain a decaying snowfall accumulator (cm) in
// the same grid pattern as the ice FDD.  Fresh loading is the classic
// natural trigger (McClung & Schaerer: 30 cm in 24 h).
private _grid = missionNamespace getVariable [QGVAR(fddGrid), createHashMap];
private _key = format ["%1_%2", round ((_pos2D select 0) / 100), round ((_pos2D select 1) / 100)];
private _entry = _grid getOrDefault [_key, [0, -1e10, 0, 0]];
_entry params ["_fdd", "_lastTick", "_ice", "_snow24"];
private _now = diag_tickTime;
private _dtH = (_now - _lastTick) / 3600;
if (_dtH > 0.5) then { _dtH = 0.5; };
private _snowfallCmH = (missionNamespace getVariable [QEGVAR(core,snowfallRate), 0]) / 10;  // mm/h -> cm/h
_snow24 = (_snow24 * exp (-_dtH / 24)) + (_snowfallCmH * _dtH);
_grid set [_key, [_fdd, _now, _ice, _snow24]];
missionNamespace setVariable [QGVAR(fddGrid), _grid];

private _trigger = (_snow24 >= 30) || (_temp > 2);

// ─── Risk from stability + trigger ──────────────────────────────────────
private _risk = 0;
if (_S < 1) then {
    // Unstable: risk scales with how far below the threshold.
    _risk = (1 - _S) * (0.6 + 0.4 * ([0, 1] select _trigger));
} else {
    // Stable but marginal: residual risk near S=1.
    if (_S < 1.5) then { _risk = (1.5 - _S) * 0.4; };
};
_risk = _risk min 1.0;

// ─── Warning level (danger scale 1-5) ───────────────────────────────────
private _warning = switch (true) do {
    case (_risk >= 0.9): { "Extreme" };
    case (_risk >= 0.7): { "High" };
    case (_risk >= 0.4): { "Moderate" };
    case (_risk >= 0.15): { "Low" };
    default              { "None" };
};

// ─── Output ─────────────────────────────────────────────────────────────
missionNamespace setVariable [QEGVAR(core,currentAvalancheRisk),     _risk];
missionNamespace setVariable [QGVAR(currentAvalancheWarning),  _warning];
missionNamespace setVariable [QGVAR(currentAvalancheStability), _S];

// Burial survival curve (minutes -> survival fraction) for rescue UX.
missionNamespace setVariable [QGVAR(avalancheBurialSurvival), [[0, 0.97], [15, 0.93], [35, 0.30], [90, 0.03]]];

_risk
