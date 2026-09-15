#include "..\script_component.hpp"
/*
 * Rain droplets on the objective lens (NVG or thermal).
 *
 * Proven recipe: TPW RAINFX (workshop 2586787720, tpw_rainfx.sqf) drops
 * refractive droplets on vehicle windscreens with:
 *
 *   drop [["\A3\data_f\ParticleEffects\Universal\Refract",1,0,1],
 *         "", "Billboard", 1, 0.05, _pos, [0,0,0],
 *         1, 1, 0, 0, [_size], [[1,1,1,0.6]], [0], 0, 0, "", "", ""];
 *
 * THREE lessons from our failed attempts (all committed history):
 *  1. A .p3d shape is only for SpaceObject particles: Billboard needs a
 *     TEXTURE as the first array element.  There is no RainDrop.p3d.
 *  2. The engine's raindrop3.paa CRASHES the game when referenced as a
 *     particle shape (ShapeLoad preNLOD format, unrecoverable).
 *  3. A procedural #(argb,...) string is REJECTED as a particle shape:
 *     "LODShape::Preload: shape '#(...)' not found / Cannot open object".
 *     Procedural works in rvmats, NOT in the particle shape slot.
 *
 * The engine's Refract texture (a3\data_f\ParticleEffects\Universal\
 * Refract, resolves to Refract.p3d + refract_ca.paa) is the real, proven
 * refractive particle: it ships in the base game, TPW uses it in
 * production, and it cannot crash.  We use the SAME drop command, placing
 * droplets a few cm in front of the eye so they read as on-lens specs.
 *
 * One droplet per tick (the sensor PFH runs at 10 Hz), gated by rain:
 * dry = no drops.  A drop is a one-shot (timerPeriod 1, lifetime 0.05),
 * so nothing persists and no source object needs cleanup.
 */
params ["_mode"];

if (!hasInterface) exitWith { 0 };

// ─── EXIT: nothing to clean up (drops are one-shot) ───────────────────────
if (_mode == "EXIT") exitWith { 0 };

private _player = call CBA_fnc_currentUnit;
if (isNil "_player" || !alive _player || cameraOn != _player) exitWith { 0 };

// ─── Gate on rain ─────────────────────────────────────────────────────────
private _rain = rain;
if !(_rain isEqualType 0) then { _rain = 0; };
if (_rain < 0.1) exitWith { 0 };

// ─── Droplet density from rain intensity ──────────────────────────────────
// Light rain: one drop every few ticks.  Heavy rain: one per tick.
// TPW uses density = rain*50 per second; at 10 Hz we scale to ~0.5*rain
// drops per tick (heavy rain ~0.5/s visible as an intermittent spec).
if (random 1 > (_rain * 0.5)) exitWith { 0 };

// ─── Droplet position: ~0.4-0.7 m in front of the eye ────────────────────
// NOT at 5-8 cm: drops that close sit inside the camera near clip plane
// and the player's own head/goggle geometry, so they are culled before
// render (the "not visible" report).  TPW puts drops at 1-3 m (their
// windscreen is a world object); ours have no surface, so we place them
// at 0.4-0.7 m - past the near plane, past the head mesh, still reading
// as small lens specs when sized at a few mm.
private _eye = eyePos _player;
private _camDir = getCameraViewDirection _player;
private _dist = 0.4 + random 0.3;
private _pos = ASLToATL (_eye vectorAdd (_camDir vectorMultiply _dist));
private _size = 0.002 + random 0.002;
private _lifetime = 0.1 + random 0.15;

if (missionNamespace getVariable [QGVAR(nvgDebug), false]) then {
    diag_log text format ["[AEE] rain drop: rain=%1 pos=%2 size=%3", _rain, _pos, _size];
};

drop [
    ["\A3\data_f\ParticleEffects\Universal\Refract", 1, 0, 1],
    "",
    "Billboard",
    1,
    _lifetime,
    _pos,
    [0, 0, 0],
    1,                      // rotation velocity
    1,                      // weight
    0,                      // volume
    0,                      // rubbing: no wind (on the lens)
    [_size],                // droplet size
    [[1, 1, 1, 0.6]],       // colour: translucent white (refraction)
    [0],                    // anim phase
    0,                      // random dir
    0,
    "",                     // onTimer
    "",                     // beforeDestroy
    ""                      // object (unattached world drop)
];

1
