#include "..\..\script_component.hpp"

/*
Infantry footfall kickup — a request to the particle pipeline (#149).

The engine throws dust for vehicles but NOT for a soldier on foot.  The
gate is unchanged: enabled, on foot, moving above walking pace, over a
surface that lifts and is not wet.  The emission and lifecycle move to
fnc_particlePipeline; this returns a request (or an empty array).

The material lifted is the SURFACE the foot lands on, and the amount scales
with the impact energy (speed squared), the surface lift and the moisture.

Gate: enabled, hasInterface, unit on foot, speed > 5 km/h, lift > 0.15.
Argument:
  0: unit (OBJECT, default the current unit)
Returns: ARRAY of requests (0 or 1).
*/

params [["_unit", call CBA_fnc_currentUnit, [objNull]]];

if (!hasInterface) exitWith { [] };
if (isNull _unit || !alive _unit) exitWith { [] };
if (!(missionNamespace getVariable [QEGVAR(core,enabled), true])) exitWith { [] };

// On foot only: a vehicle already has its own kickup.
if (!isNull objectParent _unit) exitWith { [] };

private _speed = speed _unit;                 // km/h
if (_speed < 5) exitWith { [] };              // below a brisk walk

private _pos = getPosASL _unit;
private _ground = [_pos] call FUNC(surfaceSample);
_ground params ["_material", "_colour", "_density"];

// Hardstanding and water do not kick up a visible plume.
if (_density < 0.15) exitWith { [] };

private _suppression = missionNamespace getVariable [QEGVAR(core,dustSuppression), 0.6];
if !(_suppression isEqualType 0) then { _suppression = 0.6; };
if (_suppression < 0.05) exitWith { [] };

// Speed -> strength: a brisk walk 0.15, a sprint 1.0.
private _strength = linearConversion [5, 20, _speed, 0.15, 1, true];

private _em = ["footfallDust", _pos, [_strength, _density, _colour]] call FUNC(particleEmission);
_em params ["_intensity", "_ecolour", "_rate"];
if (_intensity <= 0.005) exitWith { [] };

[createHashMapFromArray [
    ["effect", "footfallDust"],
    ["emitter", _unit],
    ["position", _pos],
    ["material", _material],
    ["lift", _density],
    ["intensity", _intensity],
    ["colour", _ecolour],
    ["rate", _rate],
    ["key", format [QGVAR(footfall_%1), netId _unit]]
]]
