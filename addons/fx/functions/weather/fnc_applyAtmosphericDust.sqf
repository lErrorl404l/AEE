#include "..\..\script_component.hpp"

/*
Atmospheric dust — a request to the particle pipeline (issue #149).

Airborne dust driven by wind speed and surface dryness.  The gate is
unchanged (wind above 5 m/s, no heavy rain, in the player's own view); the
wind/suppression/ground-state physics and the biome palette move into
fnc_particleEmission, and the lifecycle into fnc_particlePipeline.

Gate:    GVAR(enabled) && hasInterface && cameraOn is the player or their
         vehicle && wind >= 5 m/s && rain <= 0.3
Returns: ARRAY of requests (0 or 1).
*/

if (!hasInterface) exitWith { [] };
if (!(missionNamespace getVariable [QEGVAR(core,enabled), true])) exitWith { [] };

private _player = call CBA_fnc_currentUnit;
// Run in the player's own view: on foot (cameraOn == player) or in
// the player's vehicle (pilot/passenger/gunner - cameraOn is the
// vehicle).  Skip spectator/UAV-terminal/external cameras.
private _veh = vehicle _player;
if (isNil "_player" || !alive _player) exitWith { [] };
if (cameraOn != _player && {cameraOn != _veh}) exitWith { [] };

// Use the AEE wind (terrain speed-up included) so the gate and the
// emission model read the same field; fall back to the engine vector.
private _windSpeed = missionNamespace getVariable [QEGVAR(core,currentWindStr), vectorMagnitude wind];
if !(_windSpeed isEqualType 0) then { _windSpeed = vectorMagnitude wind; };
if (_windSpeed < 5) exitWith { [] };

// Rain suppresses airborne dust.
if (rain > 0.3) exitWith { [] };

private _pos = getPosASL _player;
private _em = ["atmosphericDust", _pos, []] call FUNC(particleEmission);
_em params ["_intensity", "_ecolour", "_rate"];
if (_intensity < 0.05) exitWith { [] };

[createHashMapFromArray [
    ["effect", "atmosphericDust"],
    ["emitter", _player],
    ["position", _pos],
    ["material", "dust"],
    ["lift", 0.6],
    ["intensity", _intensity],
    ["colour", _ecolour],
    ["rate", _rate],
    ["key", "atmosphericDust"]
]]
