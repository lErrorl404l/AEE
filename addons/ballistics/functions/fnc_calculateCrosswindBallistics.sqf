#include "..\script_component.hpp"

/*
Decompose the engine wind vector into crosswind and downrange components
relative to the player's weapon direction for ACE3 ballistics.

Reads:    wind (Arma engine), player weapon direction
Sets:     QGVAR(crosswind)
          QGVAR(downrangeWind)
Returns:  nothing
*/

params [["_unit", objNull, [objNull]]];
if (isNull _unit) exitWith { 0 };  // no unit on dedicated server

// ─── Wind input ──────────────────────────────────────────────────────────
// Local wind (issue #136): the spatial field at the shooter's position
// (building wake, terrain lee, canyon) replaces the single global vector.
// The global engine wind feeds the local model; getLocalWind applies the
// terrain/building/canyon modifiers and returns the local easterly/
// northerly vector.
private _pos = getPosASL _unit;
private _localWind = [_pos, _pos param [2, 0]] call EFUNC(atmos,getLocalWind);
private _windSpd  = vectorMagnitude _localWind;
private _windDir  = (_localWind select 0) atan2 (_localWind select 1);
_windDir = _windDir + 180;                    // meteorological: wind comes FROM
if (_windDir >= 360) then { _windDir = _windDir - 360; };

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
