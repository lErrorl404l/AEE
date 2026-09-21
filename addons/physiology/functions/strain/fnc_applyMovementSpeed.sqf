#include "..\..\script_component.hpp"
/*
Stamina-to-animation coupling (issue #212, #159 roadmap).

The physiology module computes the soldier's state (fatigue, cold
performance, carried load) but nothing couples it to MOVEMENT.  An
exhausted, hypothermic, overloaded soldier runs at full speed - the
invisible-state problem.  This applies setAnimSpeedCoef: the engine
multiplies the unit's animation speed directly, so fatigue becomes
VISIBLE in movement.

The physics:
  - fatigueFactor 0.30..1.0 (physiology, Borbely sleep model).  Near
    exhaustion (0.30) -> ~0.75 speed (can barely run).
  - dexterityPercent 0.40..1.0 (core, from fnc_calculateColdWeather-
    Performance).  Severe hypothermia (0.40) -> ~0.85 speed (stiff,
    clumsy).
  - carried load (the load command, 0..1 of max).  Overloaded (0.85+)
    -> ~0.90 speed.

Combined by the WEAKEST factor (the limiting constraint governs): a
fresh soldier with a heavy pack moves at the load-limited speed; an
exhausted one at the fatigue-limited speed.  The total is clamped to
0.75..1.0 - fatigue slows you, it does not cripple movement (the
engine's own stamina system still drains independently).

ACE3 guard: ace_advanced_fatigue manages its own setAnimSpeedCoef -
when present, AEE does NOT override (the same coexistence rule as the
sway factor).  AEE's factor applies only to the vanilla stamina model.

Arguments:
  0: unit (OBJECT, default player)

Returns the applied speed coefficient (0.75..1.0).
*/
params [["_unit", player, [objNull]]];
if (isNull _unit || {!local _unit}) exitWith { 1.0 };
if !(missionNamespace getVariable [QGVAR(movementSpeed), true]) exitWith { 1.0 };

// ACE3 advanced fatigue owns setAnimSpeedCoef - do not fight it.
if (isClass (configFile >> "CfgPatches" >> "ace_advanced_fatigue")) exitWith { 1.0 };

private _fatigue = missionNamespace getVariable [QGVAR(fatigueFactor), 1.0];
if !(_fatigue isEqualType 0) then { _fatigue = 1.0; };
_fatigue = _fatigue max 0.3 min 1.0;

private _dexterity = missionNamespace getVariable [QEGVAR(core,dexterityPercent), 1.0];
if !(_dexterity isEqualType 0) then { _dexterity = 1.0; };
_dexterity = _dexterity max 0.4 min 1.0;

private _load = load _unit;   // 0..1 of max carried load
_load = _load max 0 min 1;

// Each factor maps to a speed multiplier; the weakest governs.
private _fatigueSpeed = linearConversion [0.3, 1.0, _fatigue, 0.75, 1.0, true];
private _coldSpeed    = linearConversion [0.4, 1.0, _dexterity, 0.85, 1.0, true];
private _loadSpeed    = linearConversion [0.0, 0.85, _load, 1.0, 0.90, true];

private _coef = (_fatigueSpeed min _coldSpeed min _loadSpeed) max 0.75 min 1.0;
_unit setAnimSpeedCoef _coef;

_coef
