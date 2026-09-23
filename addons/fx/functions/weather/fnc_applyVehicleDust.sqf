#include "..\..\script_component.hpp"

/*
Vehicle dust kickup — a request to the particle pipeline (issue #149).

The gate is unchanged: the player must be driving a vehicle moving above
5 km/h over a surface that lifts.  The emission and the lifecycle now move
to fnc_particlePipeline; this function returns a request (or an empty
array) and never creates a source itself.  The colour comes from the
surface under the vehicle, as before.

Gate:  GVAR(enabled) && hasInterface && player is driver of a vehicle
       moving > 5 km/h && dust suppression above 0.05
Returns: ARRAY of requests (0 or 1).
*/

params [["_unit", call CBA_fnc_currentUnit, [objNull]]];

if (!hasInterface) exitWith { [] };
if (isNull _unit || !alive _unit) exitWith { [] };
if (!(missionNamespace getVariable [QEGVAR(core,enabled), true])) exitWith { [] };

private _veh = vehicle _unit;
if (_veh == _unit) exitWith { [] };
if (_unit != driver _veh) exitWith { [] };

private _suppression = missionNamespace getVariable [QEGVAR(core,dustSuppression), 0.5];
if !(_suppression isEqualType 0) then { _suppression = 0.5; };
if (_suppression < 0.05) exitWith { [] };

private _speed = speed _veh;
if (_speed < 5) exitWith { [] };

// ─── Surface material and strength ───────────────────────────────────────
private _pos = getPosASL _veh;
private _ground = [_pos] call FUNC(surfaceSample);
_ground params ["_material", "_colour", "_lift"];

// Speed -> strength: 5 km/h barely lifts, 60 km/h lifts fully.
private _strength = linearConversion [5, 60, _speed, 0.2, 1, true];

private _em = ["vehicleDust", _pos, [_strength, _lift, _colour]] call FUNC(particleEmission);
_em params ["_intensity", "_ecolour", "_rate"];
if (_intensity <= 0.01) exitWith { [] };

[createHashMapFromArray [
    ["effect", "vehicleDust"],
    ["emitter", _veh],
    ["position", _pos],
    ["material", _material],
    ["lift", _lift],
    ["intensity", _intensity],
    ["colour", _ecolour],
    ["rate", _rate],
    ["key", format [QGVAR(vehicleDust_%1), netId _veh]]
]]
