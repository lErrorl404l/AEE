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

// The carried load: the equipment library's per-slot signature.  The
// combined entry (index 5) holds the summed weight (uniform + vest +
// helmet + goggles + pack + contents) in kg.  A 30 kg combat load
// slows the soldier (the issue #119 library feeds #212).  Light patrol
// ~15 kg -> full speed, overloaded ~45 kg -> 0.85.
private _equip = [_unit] call FUNC(getEquipmentProperties);
private _combined = _equip select 5;
private _load = _combined select 0;

// Clothing insulation shifts the felt wind chill toward the air
// temperature (the wind-chill index is for exposed skin; clo 1.0 is a
// full combat ensemble).  The insulation correction is a simple
// exponential: at clo 0.75 (combat uniform) the soldier feels ~65 % of
// the wind-chill deficit; at clo 2.5 (winter parka) ~15 %.
private _airTemp = missionNamespace getVariable [QEGVAR(core,currentTemperature), 15];
if !(_airTemp isEqualType 0) then { _airTemp = 15; };
private _wct = missionNamespace getVariable [QEGVAR(core,windChillTemp), _airTemp];
if !(_wct isEqualType 0) then { _wct = _airTemp; };

// Dexterity is a HAND function.  The hand feels its OWN temperature -
// the wind chill insulated by the handwear (Gonzalez 1998 measured:
// light duty glove 0.86 clo, heavy duty 1.05, Arctic mitten 1.46).
private _gloveClo = [_unit] call FUNC(getGloveProperties);
private _handWct = _airTemp + (_wct - _airTemp) * (exp (-_gloveClo));

// Cold-exposure duration: Daanen 2009 (Ind Health 47:262) - manual
// dexterity loss = 0.162 x WCET x exposure^0.38.  The loss grows
// sub-linearly with how long the hand has been cold.  Accumulate the
// exposure on the 1 s coupling loop; reset when the hand warms.
private _exposure = _unit getVariable [QGVAR(coldExposureSec), 0];
if (_handWct < 0) then {
    _unit setVariable [QGVAR(coldExposureSec), _exposure + 1];
    _exposure = _exposure + 1;
} else {
    _unit setVariable [QGVAR(coldExposureSec), 0];
    _exposure = 0;
};
private _exposureMin = _exposure / 60;
private _daanenLoss = 0.162 * (0 max -_handWct) * (_exposureMin ^ 0.38);

// Glove thickness penalty (Bensel 1993): even in warmth, thick gloves
// cost fine motor control - test time rises linearly with thickness,
// grip anchor -31 % at 3.1 mm.  Thickness maps from the handwear clo
// (light ~1 mm, heavy ~2 mm, mitten ~3.5 mm); bare hands have none.
private _benselLoss = if (_gloveClo > 0.1) then {
    linearConversion [0.86, 1.46, _gloveClo, 1.0, 3.5, true] * 10
} else { 0 };

// Net dexterity: the Heus 1995 curve on the HAND temperature, minus
// the Daanen cold-exposure loss and the Bensel glove penalty.  The
// floor is 10 (severely numb), ceiling 100 (warm, bare).
private _dexterity = ((90 + 2 * _handWct) - _daanenLoss - _benselLoss) max 10 min 100;

// Each factor maps to a speed multiplier; the weakest governs.
private _fatigueSpeed = linearConversion [0.3, 1.0, _fatigue, 0.75, 1.0, true];
private _coldSpeed    = linearConversion [10.0, 100.0, _dexterity, 0.85, 1.0, true];
private _loadSpeed    = linearConversion [15.0, 45.0, _load, 1.0, 0.85, true];

private _coef = (_fatigueSpeed min _coldSpeed min _loadSpeed) max 0.75 min 1.0;
_unit setAnimSpeedCoef _coef;

_coef
