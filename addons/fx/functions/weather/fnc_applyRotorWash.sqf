#include "..\..\script_component.hpp"

/*
Rotor wash dust — a request to the particle pipeline (issue #149).

A helicopter close to the ground lifts the surface material into its
outwash: brownout over sand, whiteout over snow.  The gate and the
downwash physics (fnc_calculateDownwash) are unchanged; the emission and
lifecycle move to fnc_particlePipeline.  The emitter radius still follows
the outwash, so a stronger flow throws the material further out.

Gate: enabled, hasInterface, a helicopter in ground effect (speed <= 60),
   over a surface that lifts, with entrainment above zero.

Argument:
  0: aircraft (OBJECT, default the player's vehicle)
Returns: ARRAY of requests (0 or 1).
*/

params [["_aircraft", vehicle (call CBA_fnc_currentUnit), [objNull]]];

if (!hasInterface) exitWith { [] };
if (isNull _aircraft || !alive _aircraft) exitWith { [] };
if (!(missionNamespace getVariable [QEGVAR(core,enabled), true])) exitWith { [] };

// Helicopters only: a fixed-wing rotor wash is not this phenomenon.
if !(_aircraft isKindOf "Helicopter") exitWith { [] };

// Ground effect is a low, slow condition.
if (speed _aircraft > 60) exitWith { [] };

private _pos = getPosASL _aircraft;
private _ground = [_pos] call FUNC(surfaceSample);
_ground params ["_material", "_colour", "_lift"];
if (_lift < 0.15) exitWith { [] };

// ─── The physics: is the flow above the entrainment threshold? ────────────
private _wash = [_aircraft, _material] call FUNC(calculateDownwash);
_wash params ["_entrainment", "_threshold", "_outwash", "_flux"];
if (_entrainment <= 0) exitWith { [] };

private _suppression = missionNamespace getVariable [QEGVAR(core,dustSuppression), 0.6];
if !(_suppression isEqualType 0) then { _suppression = 0.6; };
_entrainment = _entrainment * _suppression;
if (_entrainment < 0.02) exitWith { [] };

private _em = ["rotorWash", _pos, [_entrainment, _lift, _colour]] call FUNC(particleEmission);
_em params ["_intensity", "_ecolour", "_rate"];
if (_intensity <= 0.005) exitWith { [] };

[createHashMapFromArray [
    ["effect", "rotorWash"],
    ["emitter", _aircraft],
    ["position", _pos],
    ["material", _material],
    ["lift", _lift],
    ["intensity", _intensity],
    ["colour", _ecolour],
    ["rate", _rate],
    // The ring radius follows the outwash: a stronger flow throws the
    // material further out before it rises.
    ["radius", 4 + (_outwash * 0.35)],
    ["key", format [QGVAR(rotorWash_%1), netId _aircraft]]
]]
