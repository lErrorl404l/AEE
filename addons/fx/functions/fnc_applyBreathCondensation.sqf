#include "..\script_component.hpp"

/*
Breath condensation puff — visible exhalation in cold, calm air.

Reads QGVAR(currentTemperature), QGVAR(windSpeed).
Gates on GVAR(environmentalEnabled).  Creates a small white particle
cloud at the player's eye position when temp < 5 C and wind < 5 m/s.

Uses #particlesource with lifecycle management.  Stacking guard
via QGVAR(breathCondensation) mission variable.
*/

if (!EGVAR(core,environmentalEnabled)) exitWith {};

private _temp      = missionNamespace getVariable [QEGVAR(core,currentTemperature), 20];
private _windSpeed = vectorMagnitude wind;

if (_temp >= 5 || (_windSpeed >= 5)) exitWith {};

private _player = call CBA_fnc_currentUnit;
if (isNil "_player" || !alive _player || cameraOn != _player) exitWith {};

// Guard: skip if existing source is alive (prevents stacking)
private _existing = missionNamespace getVariable [QGVAR(breathCondensation), objNull];
if (!isNull _existing && alive _existing) exitWith {};

// Budget check: skip if over particle ceiling
if !([] call FUNC(checkParticleBudget)) exitWith {};

// Create particle source at eye position
private _headPos = eyePos _player;
private _source = "#particlesource" createVehicleLocal _headPos;
missionNamespace setVariable [QGVAR(breathCondensation), _source];
_source call FUNC(registerParticleSource);

_source setParticleCircle [0, [0, 0, 0]];
_source setParticleRandom [0, [0, 0, 0], [0, 0, 0.2], 0, 0.2, [0, 0, 0, 0], 0, 0];
_source setParticleParams [
    ["\a3\data_f\ParticleEffects\Universal\Universal", 16, 12, 8],
    "",
    "Billboard",
    1,                          // sort
    2,                          // lifeTime
    [0, 0, 0],                 // position (at source origin)
    [0, 0, 0.2],               // velocity (gentle upward)
    0, 2.5, 2, 0.2,            // weight, volume, rubbing, size
    [0.04, 0.12],              // size progression
    [[1,1,1,0.4],[1,1,1,0.1],[1,1,1,0]], // colour fade white
    0.5,                      // animSpeed (scalar)
    1,                         // angle
    0,                         // random dir
    "", "",                    // on surface, before destroy
    _player,                   // attach to
    0, true                    // bounce, imprecise
];
_source setDropInterval 100;   // ponytail: one-shot burst, high interval

// Auto-cleanup after particle lifetime
[_source] spawn {
    params ["_source"];
    sleep 3;
    deleteVehicle _source;
};
