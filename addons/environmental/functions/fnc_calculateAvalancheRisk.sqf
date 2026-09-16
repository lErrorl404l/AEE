#include "..\script_component.hpp"

/*
Avalanche risk index (0-1) for mountainous terrain.

Requires Snow or Frozen ground state.  Risk factors:
  • Slope angle (estimated from terrain height samples) — risk rises from
    ~20°, peaks at 30–40°, falls above ~50° (release zones cluster at
    30–45°; Schweizer et al., 2003)
  • Wind loading  (>8 m/s deposits snow on lee slopes)
  • Temperature spike (rapid warm-up destabilises snowpack)
  • Rain on snow (lubricates layers)

Sets:
  QEGVAR(core,currentAvalancheRisk)     — float 0-1
  QGVAR(currentAvalancheWarning)  — "None" / "Low" / "Moderate" / "High" / "Extreme"
*/

params [["_posASL", [], [[]]]];

private _groundState = missionNamespace getVariable [QEGVAR(core,groundState), "Normal"];

// ─── Early exit: no snowpack ────────────────────────────────────────────
if (_groundState != "Snow" && (_groundState != "Frozen")) exitWith {
    missionNamespace setVariable [QEGVAR(core,currentAvalancheRisk),    0];
    missionNamespace setVariable [QGVAR(currentAvalancheWarning), "None"];
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

// ─── Slope estimate from 4 cardinal samples at 50 m radius ─────────────
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

// ─── Risk components ─────────────────────────────────────────────────────
// Slope: peak at 35°, zero at 15° and 55° (Schweizer et al., 2003)
private _slopeRisk = 1 - (abs (_slopeDeg - 35) / 20);
_slopeRisk = _slopeRisk max 0 min 1;

// Wind loading: >8 m/s deposits drifted snow
private _windSpd = vectorMagnitude wind;
private _windFactor = 0;
if (_windSpd > 8) then {
    _windFactor = ((_windSpd - 8) / 20) min 0.2;
};

// Temperature spike — rapid warm-up weakens bonds
private _temp = EGVAR(core,currentTemperature);
if (isNil "_temp") then { _temp = 0; };
private _tempFactor = 0;
if (_temp > 0) then {
    _tempFactor = ((_temp - 0) / 20) * 0.15 min 0.15;
};

// Rain on snow — lubricates slide plane
private _rainFactor = 0;
if (_groundState == "Snow" && rain > 0) then {
    _rainFactor = (rain * 0.15) min 0.15;
};

private _risk = (_slopeRisk + _windFactor + _tempFactor + _rainFactor) min 1.0;

// ─── Warning level ──────────────────────────────────────────────────────
private _warning = switch (true) do {
    case (_risk >= 0.9): { "Extreme" };
    case (_risk >= 0.7): { "High" };
    case (_risk >= 0.4): { "Moderate" };
    case (_risk >= 0.2): { "Low" };
    default              { "None" };
};

// ─── Output ─────────────────────────────────────────────────────────────
missionNamespace setVariable [QEGVAR(core,currentAvalancheRisk),    _risk];
missionNamespace setVariable [QGVAR(currentAvalancheWarning), _warning];
_risk
