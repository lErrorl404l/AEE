#include "..\script_component.hpp"

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

if (!EGVAR(core,enabled)) exitWith {};

private _player = call CBA_fnc_currentUnit;
if (isNil "_player" || !alive _player || cameraOn != _player) exitWith {};

// Need rain
if (rain < 0.1) exitWith {};

// ─── Overhead cover check (from TPW rainfx) ─────────────────────────────
// Cast a ray from eye position straight up 50 m. If it hits something,
// the player is sheltered and rain drops are suppressed.
private _eyePos = eyePos _player;
private _highPos = _eyePos vectorAdd [0, 0, 50];
if (lineIntersects [_eyePos, _highPos]) exitWith {};

// ─── Rain intensity → particle parameters ───────────────────────────────
private _dropInterval = linearConversion [0.1, 1, rain, 0.006, 0.002, true];
private _animFactor   = linearConversion [0.1, 1, rain, 0.1, 0.2, true];
private _radius       = 18;

private _drops = "#particlesource" createVehicleLocal position _player;
_drops setParticleCircle [_radius, [0, 0, 0]];
_drops setParticleRandom [0.2, [_radius, _radius, 0], [0, 0, 1], 13, 0.5, [0, 0, 0, 0], 1, 0];
_drops setParticleParams [
    ["\A3\Data_F_Mark\ParticleEffects\Universal\waterBallonExplode_01", 4, 0, 16, 0],
    "",
    "Billboard",
    1,                              // sort
    0.4,                            // lifeTime
    [0, 0, 25],                     // position (above player)
    [0, 0, 0.5],                   // velocity (falling)
    0,                              // weight
    18,                             // volume
    7.9,                            // rubbing
    [0.05, _animFactor + 0.2],      // size
    [[0.5, 0.5, 0.5, 1], [0.5, 0.5, 0.5, 1]], // colour
    [2],                            // animSpeed
    1,                              // angle
    0,                              // random dir
    "",                             // on surface
    "",                             // before destroy
    _player,                        // attach to
    0, true                         // bounce, imprecise
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
