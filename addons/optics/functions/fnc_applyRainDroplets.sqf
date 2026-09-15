#include "..\script_component.hpp"
/*
 * Rain droplets on the objective lens (NVG or thermal).
 *
 * PROVEN RECIPE (TPW RAINFX, workshop 2586787720, tpw_rainfx.sqf lines
 * 79-89 — the goggles emitter):
 *
 *   _gograinemitter = "#particlesource" createVehicleLocal [0,0,0];
 *   _logic = "logic" createVehicleLocal [0,0,0];
 *   _gograinemitter attachto [_logic,[0,0,0]];
 *   _logic attachto [player,[0,0,0],"HEAD"];
 *   _gograinemitter setParticleParams [["\A3\data_f\ParticleEffects\
 *     Universal\Refract",1,0,1], "", "Billboard", 1, 0.05, [0,0,0],
 *     [0,0,0], 1, 1, 0, 0, [0.1], [[1,1,1,1]], [0], 0, 0, "", "", _logic];
 *   _gograinemitter setDropInterval _int;
 *
 * WHY THIS AND NOT drop: the raw `drop` command with the Refract shape
 * fails with "NOID refract.p3d #cloudlet" — Refract is a CLOUDLET class
 * and can only be emitted through setParticleParams on a #particlesource,
 * not the one-shot drop.  TPW's windscreen drops use drop (their own
 * generic path); their GOGGLES fx uses the emitter below.  We need the
 * goggles path.
 *
 * Three more lessons from our failed attempts (all in commit history):
 *  1. The engine raindrop3.paa CRASHES the game when used as a particle
 *     shape (ShapeLoad preNLOD format, unrecoverable).
 *  2. A procedural #(argb,...) string is REJECTED in the shape slot
 *     ("LODShape::Preload: shape '#(...)' not found").
 *  3. A bare drop with Refract gives "NOID refract.p3d #cloudlet".
 *
 * The emitter is attached to a logic on the player's HEAD memory point,
 * so droplets track the head exactly and stay on the lens regardless of
 * where the player looks.  Position is memory-point-relative [0,0,0].
 */
params ["_mode"];

if (!hasInterface) exitWith { 0 };

private _src = missionNamespace getVariable [QGVAR(rainDropSource), objNull];
private _logic = missionNamespace getVariable [QGVAR(rainDropLogic), objNull];

// ─── EXIT: destroy source + logic ─────────────────────────────────────────
if (_mode == "EXIT") then {
    if (!isNull _src) then {
        deleteVehicle _src;
        missionNamespace setVariable [QGVAR(rainDropSource), objNull];
    };
    if (!isNull _logic) then {
        deleteVehicle _logic;
        missionNamespace setVariable [QGVAR(rainDropLogic), objNull];
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
    if (!isNull _logic) then {
        deleteVehicle _logic;
        missionNamespace setVariable [QGVAR(rainDropLogic), objNull];
    };
    0
};

// ─── Create the head-attached emitter once, then drive the interval ───────
if (isNull _src) then {
    _src = "#particlesource" createVehicleLocal [0, 0, 0];
    _logic = "logic" createVehicleLocal [0, 0, 0];
    _src attachTo [_logic, [0, 0, 0]];
    _logic attachTo [_player, [0, 0, 0], "HEAD"];

    _src setParticleCircle [0.004, [0.004, 0.004, 0.004]];
    _src setParticleRandom [0, [0.002, 0.002, 0], [0, 0, 0], 0, 0, [0, 0, 0, 0], 0, 0];
    _src setParticleParams [
        ["\A3\data_f\ParticleEffects\Universal\Refract", 1, 0, 1],
        "",                                       // animation
        "Billboard",                              // type: faces camera
        1,                                        // timer period (s)
        0.3,                                      // lifetime (s)
        [0, 0, 0],                                // pos: HEAD memory point relative
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
        _logic                                    // object: HEAD-attached logic
    ];

    missionNamespace setVariable [QGVAR(rainDropSource), _src];
    missionNamespace setVariable [QGVAR(rainDropLogic), _logic];
};

// Drop interval scales with rain: heavy rain = ~0.1 s, light = ~0.5 s.
private _interval = 0.5 / (_rain + 0.2);
_src setDropInterval (_interval max 0.05);
_interval
