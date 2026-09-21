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
  - cold: the unit's own dexterity from the felt wind chill (air
    temperature + the insulation-corrected wind-chill deficit).
    Severe hypothermia (10 on the 0..100 dexterity scale) -> ~0.85
    speed (stiff, clumsy).  The insulation (clo, the issue #119
    library) shifts the felt wind chill toward the air temperature:
    a winter-parka soldier moves better than a shirt-sleeve one.
  - carried load (the equipment library total, kg).  Overloaded
    (45 kg) -> ~0.85 speed.

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

// The carried load + insulation: the equipment library's total weight
// (uniform + vest + helmet + pack + contents) in kg and the combined
// insulation in clo.  A 30 kg combat load slows the soldier (the issue
// #119 library feeds #212).  Light patrol ~15 kg -> full speed,
// overloaded ~45 kg -> 0.85.
private _equip = [_unit] call FUNC(getEquipmentProperties);
private _load = _equip select 0;
private _clo = _equip select 3;

// Clothing insulation shifts the felt wind chill toward the air
// temperature (the wind-chill index is for exposed skin; clo 1.0 is a
// full combat ensemble).  The insulation correction is a simple
// exponential: at clo 0.75 (combat uniform) the soldier feels ~65 % of
// the wind-chill deficit; at clo 2.5 (winter parka) ~15 %.  The unit's
// own dexterity is computed from the felt temperature.  The dexterity
// curve is 90 + 2*WCT (Heus 1995), floor 10, on the same 0..100 scale
// the cold-weather model publishes.
private _airTemp = missionNamespace getVariable [QEGVAR(core,currentTemperature), 15];
if !(_airTemp isEqualType 0) then { _airTemp = 15; };
private _wct = missionNamespace getVariable [QEGVAR(core,windChillTemp), _airTemp];
if !(_wct isEqualType 0) then { _wct = _airTemp; };
private _feltWct = _airTemp + (_wct - _airTemp) * (exp (-_clo));
private _dexterity = (90 + 2 * _feltWct) max 10 min 100;

// Each factor maps to a speed multiplier; the weakest governs.
private _fatigueSpeed = linearConversion [0.3, 1.0, _fatigue, 0.75, 1.0, true];
private _coldSpeed    = linearConversion [10.0, 100.0, _dexterity, 0.85, 1.0, true];
private _loadSpeed    = linearConversion [15.0, 45.0, _load, 1.0, 0.85, true];

private _coef = (_fatigueSpeed min _coldSpeed min _loadSpeed) max 0.75 min 1.0;
_unit setAnimSpeedCoef _coef;

_coef
