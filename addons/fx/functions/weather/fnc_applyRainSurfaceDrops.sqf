#include "..\..\script_component.hpp"

/*
Rain surface drops — particle effect of rain hitting the ground
around the player.

Pattern adapted from TPW MODS rainfx (tpw_rainfx.sqf) and
Real Lighting rain drops (fn_rainDrop.sqf).

Uses lineIntersects to check overhead cover — only spawns drops
when the player is exposed to rain (not under a roof or canopy).

Gate:    GVAR(enabled) && hasInterface
Reads:   rain (engine variable), wind
Emits:   Billboard water-drop particles in a circle around player
*/

if (!(missionNamespace getVariable [QEGVAR(core,enabled), true])) exitWith {};

private _player = call CBA_fnc_currentUnit;
// Run in the player's own view: on foot (cameraOn == player) or in
// the player's vehicle (pilot/passenger/gunner - cameraOn is the
// vehicle).  Skip spectator/UAV-terminal/external cameras.
private _veh = vehicle _player;
if (isNil "_player" || !alive _player) exitWith {};
if (cameraOn != _player && {cameraOn != _veh}) exitWith {};

// Need rain
if (rain < 0.1) exitWith {};

private _density = missionNamespace getVariable [QGVAR(rainDropDensity), 0.006];

// Guard: skip if an existing drops source is still alive (prevents stacking)
private _existing = missionNamespace getVariable [QGVAR(rainSurfaceDrops), objNull];
if (!isNull _existing && alive _existing) exitWith {};

// ─── Overhead cover check (from TPW rainfx) ─────────────────────────────
// Cast a ray from eye position straight up 50 m. If it hits something,
// the player is sheltered and rain drops are suppressed.
private _eyePos = eyePos _player;
private _highPos = _eyePos vectorAdd [0, 0, 50];
if (lineIntersects [_eyePos, _highPos]) exitWith {};

// ─── Rain intensity → particle parameters ───────────────────────────────
private _dropInterval = linearConversion [0.1, 1, rain, _density, _density / 3, true];
private _animFactor   = linearConversion [0.1, 1, rain, 0.1, 0.2, true];
private _radius       = 18;

// Wind drift — scale wind vector for gentle horizontal push
private _windDrift = wind vectorMultiply 0.3;

private _drops = "#particlesource" createVehicleLocal position _player;
missionNamespace setVariable [QGVAR(rainSurfaceDrops), _drops];
_drops setParticleCircle [_radius, [0, 0, 0]];
// setParticleRandom takes 10 elements (wiki: lifeTimeVar, positionVar,
// moveVelocityVar, rotationVelocityVar, sizeVar, colorVar,
// directionPeriodVar, directionIntensityVar, angleVar, bounceOnSurfaceVar).
// The 8-element form shifted the parser and threw "Type Array, expected
// Number" on the color element.
_drops setParticleRandom [0.2, [_radius, _radius, 0], [0, 0, 1], 13, 0.5, [0, 0, 0, 0], 1, 0, 45, 0];
_drops setParticleParams [
    ["\A3\Data_F_Mark\ParticleEffects\Universal\waterBallonExplode_01", 16, 12, 9, 0], // shape: [path, nth, row, column, loop]
    "",                          // animationName (obsolete, must be empty)
    "Billboard",                 // type
    1,                           // timerPeriod
    0.4,                         // lifetime
    [0, 0, 25],                  // position (above player)
    _windDrift vectorAdd [0, 0, 0.5], // moveVelocity (falling + wind drift)
    0,                           // rotationVelocity (number, rotations/s)
    0,                           // weight
    18,                          // volume
    7.9,                         // rubbing
    [0.05, _animFactor + 0.2],   // size progression (array of numbers)
    [[0.5, 0.5, 0.5, 1], [0.5, 0.5, 0.5, 1]], // colour progression (array of RGBA)
    [2],                         // animationPhase (array of numbers)
    1,                           // randomDirectionPeriod
    0,                           // randomDirectionIntensity
    "",                          // onTimer script
    "",                          // beforeDestroy script
    _player,                     // object to attach
    0,                           // angle (radians, optional)
    true,                        // onSurface (boolean, optional)
    0.5                          // bounceOnSurface (number, optional)
];
_drops setDropInterval _dropInterval;

// ─── Auto-cleanup: delete when rain stops or after timeout
[_drops, _player] spawn {
    params ["_source", "_owner"];
    waitUntil {
        sleep 5;
        rain < 0.1 || isNull _owner || !alive _owner || cameraOn != _owner
    };
    deleteVehicle _source;
};
