#include "..\script_component.hpp"

/*
Decompose the engine wind vector into crosswind and downrange components
relative to the player's weapon direction for ACE3 ballistics.

Reads:    wind (Arma engine), player weapon direction
Sets:     EGVAR(core,currentWind) = [crosswind, downrange]
          QGVAR(crosswind)
          QGVAR(downrangeWind)
Returns:  nothing
*/

params [["_unit", call CBA_fnc_currentUnit, [objNull]]];

// ─── Wind input ──────────────────────────────────────────────────────────
private _windData = wind;                                   // [speed_mps, direction_deg]
private _windSpd  = _windData param [0, 0];
private _windDir  = _windData param [1, 0];                 // meteorological: wind comes FROM

// ─── Player's aiming direction ───────────────────────────────────────────
private _wDir = _unit weaponDirection currentWeapon _unit;
private _playerDir = if (_wDir isNotEqualTo [0,0,0]) then {
    // Convert world-space direction vector to compass heading
    private _hdg = (_wDir select 0) atan2 (-(_wDir select 2));
    if (_hdg < 0) then { _hdg + 360 } else { _hdg }
} else {
    getDirVisual _unit                                      // fallback — eye/body direction
};

// ─── Decompose ───────────────────────────────────────────────────────────
// Crosswind   = perpendicular to aim direction (positive = from shooter's right)
// Downrange   = parallel to aim direction    (positive = tailwind)
private _crosswind = _windSpd * sin (_windDir - _playerDir);
private _downrange = _windSpd * cos (_windDir - _playerDir);

// ─── Persist ─────────────────────────────────────────────────────────────
// Note: we do NOT overwrite EGVAR(core,currentWind) here — that variable
// holds the raw engine wind and is consumed by other update functions.
// ACE3 ballistics reads Arma's `wind` command (set via setWind in fn_updateWind),
// not this decomposed vector. The decomposed components are stored for
// any external mod that wants windage data.
missionNamespace setVariable [QGVAR(crosswind),      _crosswind];
missionNamespace setVariable [QGVAR(downrangeWind),  _downrange];
