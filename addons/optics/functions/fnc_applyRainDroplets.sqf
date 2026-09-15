#include "..\script_component.hpp"
/*
 * Rain droplets on the objective lens (NVG or thermal).
 *
 * HOW THIS WORKS (and why every previous attempt was invisible):
 *
 * The engine's own rain renders fine through NVG/thermal/normal (verified
 * in-game), so 3D particles DO composite through the post-process.  Our
 * droplets were invisible because the emitter was attached to the player's
 * HEAD memory point with [0,0,0] offset — that point is at the TOP of the
 * head, BEHIND the first-person camera eye, so every particle spawned
 * outside the view frustum.
 *
 * FIX: a world-space emitter repositioned every tick to
 * eyePos + cameraDir * 0.1 (a few cm in front of the eye).  Droplets then
 * spawn exactly in view, like the engine's own rain.
 *
 * PROVEN RECIPE for the PARTICLE PARAMS (TPW RAINFX workshop 2586787720,
 * tpw_rainfx.sqf lines 79-89): #particlesource + Refract + Billboard.
 * The Refract cloudlet can only be emitted through setParticleParams on a
 * #particlesource, NOT the one-shot drop ("NOID refract.p3d #cloudlet").
 */
params ["_mode"];

if (!hasInterface) exitWith { 0 };

private _src = missionNamespace getVariable [QGVAR(rainDropSource), objNull];

// ─── EXIT: destroy source ─────────────────────────────────────────────────
if (_mode == "EXIT") then {
    if (!isNull _src) then {
        deleteVehicle _src;
        missionNamespace setVariable [QGVAR(rainDropSource), objNull];
    };
    0
};

private _player = call CBA_fnc_currentUnit;
if (isNil "_player" || !alive _player || cameraOn != _player) exitWith { 0 };

// ─── Gate on rain ─────────────────────────────────────────────────────────
private _rain = rain;
if !(_rain isEqualType 0) then { _rain = 0; };
if (_rain < 0.1) then {
    if (!isNull _src) then {
        deleteVehicle _src;
        missionNamespace setVariable [QGVAR(rainDropSource), objNull];
    };
    0
};

// ─── Create the emitter once ───────────────────────────────────────────────
// NOT attached to the player's HEAD memory point.  That memory point sits
// at the TOP of the head, which in first person is BEHIND and ABOVE the
// camera eye: particles spawn outside the view frustum and are never seen
// (this was the failure across all previous attempts - the emitter ran,
// drops fired, RPT clean, nothing visible).  The engine's own rain works
// because it is WORLD-space around the player and enters the frustum.
//
// FIX: the emitter is a free world-space object, repositioned every TICK
// to eyePos + cameraDir * 0.1 (a few cm in front of the eye).  Particles
// then spawn exactly in the view, like the engine's own rain.  Cheap:
// one setPosASL per tick.
if (isNull _src) then {
    _src = "#particlesource" createVehicleLocal [0, 0, 0];

    _src setParticleCircle [0.004, [0.004, 0.004, 0.004]];
    _src setParticleRandom [0, [0.002, 0.002, 0], [0, 0, 0], 0, 0, [0, 0, 0, 0], 0, 0];
    _src setParticleParams [
        ["\A3\data_f\ParticleEffects\Universal\Refract", 1, 0, 1],
        "",                                       // animation
        "Billboard",                              // type: faces camera
        1,                                        // timer period (s)
        0.3,                                      // lifetime (s)
        [0, 0, 0],                                // pos: relative to emitter
        [0, 0, 0],                                // moveVelocity: none (on lens)
        1,                                        // rotation velocity
        1,                                        // weight
        0,                                        // volume
        0,                                        // rubbing: no wind (on lens)
        [0.05, 0.08],                             // size: 5-8 cm (ACE3 uses 0.1
                                                  //   and it IS visible; 8 mm was
                                                  //   lost in the NVG grain)
        // Colour: default translucent white (refraction).  Debug hook:
        // set aee_optics_rainDropColor to a bright colour (e.g. magenta
        // [1,0,1,1] or yellow [1,1,0,1]) to make droplets unmistakable
        // against the green NVG image while verifying the emitter works.
        missionNamespace getVariable [QGVAR(rainDropColor),
            if (missionNamespace getVariable [QGVAR(nvgDebug), false]) then {
                [[1, 0, 1, 1], [1, 0, 1, 0.8]]
            } else {
                [[1, 1, 1, 1], [1, 1, 1, 0.8]]
            }
        ],
        [0],                                      // anim phase
        0,                                        // random dir
        0,
        "",                                       // onTimer
        "",                                       // beforeDestroy
        objNull                                   // object: none (world emitter)
    ];

    missionNamespace setVariable [QGVAR(rainDropSource), _src];
};

// ─── Reposition to the camera eye every tick ──────────────────────────────
// World-space emitter parked a few cm in front of the eye, following the
// camera direction so droplets sit on the lens wherever the player looks.
private _eye = eyePos _player;
private _camDir = getCameraViewDirection _player;
_src setPosASL (_eye vectorAdd (_camDir vectorMultiply 0.1));

// Drop interval scales with rain: heavy rain = ~0.1 s, light = ~0.5 s.
private _interval = 0.5 / (_rain + 0.2);
_src setDropInterval (_interval max 0.05);
_interval

