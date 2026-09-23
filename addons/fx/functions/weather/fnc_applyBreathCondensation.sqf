#include "..\..\script_component.hpp"

/*
Breath condensation puff — visible exhalation in cold, calm air.

Reads QGVAR(currentTemperature), QGVAR(windSpeed).
Gates on GVAR(environmentalEnabled).  Creates a small white particle
cloud at the player's eye position when temp < 5 C and wind < 5 m/s.

Uses #particlesource with lifecycle management.  Stacking guard
via QGVAR(breathCondensation) mission variable.
*/

if (!(missionNamespace getVariable [QEGVAR(core,environmentalEnabled), true])) exitWith {};

private _temp      = missionNamespace getVariable [QEGVAR(core,currentTemperature), 20];
private _windSpeed = vectorMagnitude wind;

if (_temp >= 5 || (_windSpeed >= 5)) exitWith {};

private _player = call CBA_fnc_currentUnit;
// Run in the player's own view: on foot (cameraOn == player) or in
// the player's vehicle (pilot/passenger/gunner - cameraOn is the
// vehicle).  Skip spectator/UAV-terminal/external cameras.
private _veh = vehicle _player;
if (isNil "_player" || !alive _player) exitWith {};
if (cameraOn != _player && {cameraOn != _veh}) exitWith {};

// Guard: skip if existing source is alive (prevents stacking)
private _existing = missionNamespace getVariable [QGVAR(breathCondensation), objNull];
if (!isNull _existing && alive _existing) exitWith {};

// Allocate from the shared budget by priority (issue #149).  Breath
// condensation is a high-visibility player effect, so it outranks ambient
// dust but sits below the weather extremes.
if !(["breath", 65, 20] call FUNC(particleAllocate)) exitWith {};

// Create particle source at eye position
private _headPos = eyePos _player;
private _source = "#particlesource" createVehicleLocal _headPos;
missionNamespace setVariable [QGVAR(breathCondensation), _source];
[_source, "breath", 65, 20, 3, ""] call FUNC(registerParticleSource);

_source setParticleCircle [0, [0, 0, 0]];
_source setParticleRandom [0, [0, 0, 0], [0, 0, 0.2], 0, 0.2, [0, 0, 0, 0], 0, 0];
_source setParticleParams [
    ["\a3\data_f\ParticleEffects\Universal\Universal", 16, 12, 9, 0], // shape: [path, nth, row, column, loop]
    "",                          // animationName (obsolete, must be empty)
    "Billboard",                 // type
    1,                           // timerPeriod
    2,                           // lifetime
    [0, 0, 0],                   // position (at source origin)
    [0, 0, 0.2],                 // moveVelocity (gentle upward)
    0,                           // rotationVelocity (number, rotations/s)
    2.5,                         // weight
    2,                           // volume
    0.2,                         // rubbing
    [0.04, 0.12],                // size progression (array of numbers)
    [[1,1,1,0.4],[1,1,1,0.1],[1,1,1,0]], // colour fade white (array of RGBA)
    [0.5],                       // animationPhase (array of numbers)
    1,                           // randomDirectionPeriod
    0,                           // randomDirectionIntensity
    "",                          // onTimer script
    "",                          // beforeDestroy script
    _player,                     // object to attach
    0,                           // angle (radians, optional)
    true,                        // onSurface (boolean, optional)
    0.5                          // bounceOnSurface (number, optional)
];
_source setDropInterval 100;   // ponytail: one-shot burst, high interval

// Auto-cleanup after particle lifetime
[_source] spawn {
    params ["_source"];
    sleep 3;
    deleteVehicle _source;
};
