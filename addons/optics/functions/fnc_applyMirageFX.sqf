#include "..\script_component.hpp"

/*
Heat haze / mirage visual effect — Refract particle at ground level.

Reads QGVAR(mirageIntensity) (0–1) produced by fnc_calculateMirageIntensity.
Gates on EGVAR(core,opticsEnabled).

Uses a Refract #particlesource attached to the player at ground level
to simulate the refractive distortion of hot air rising from sun-baked
surfaces.  The particle alpha scales with intensity.

Reference values (from workshop mod study):
  • Natural mirage: alpha 0.05–0.15, size 1–3 m at ground level
  • Must gate on hot weather, low viewing angles, near-horizon
  • Antistasi intense fire: 0.25; ground shimmer: 0.05–0.15

Adapted from TPW MODS heat haze and vanilla Arma 3 heatDistortion
effect patterns.
*/

if (!EGVAR(core,opticsEnabled)) exitWith {};

private _intensity = missionNamespace getVariable [QGVAR(mirageIntensity), 0];
private _player    = call CBA_fnc_currentUnit;
if (isNil "_player" || !alive _player || cameraOn != _player) exitWith {};

// Guard: skip if existing mirage source is alive (prevents stacking)
private _existing = missionNamespace getVariable [QGVAR(mirageSource), objNull];
if (!isNull _existing && alive _existing) exitWith {};

if (_intensity > 0.02) then {
    // Create refract particle at ground level near player
    private _pos = getPosASL _player;
    _pos set [2, (_pos select 2) + 0.5]; // slightly above ground

    private _mirage = "#particlesource" createVehicleLocal _pos;
    _mirage attachTo [_player, [0, 3, 0.5]]; // in front, at ground

    private _alpha = linearConversion [0, 1, _intensity, 0.05, 0.15, true];
    private _size  = linearConversion [0, 1, _intensity, 1, 3, true];

    _mirage setParticleParams [
        ["\A3\data_f\particleeffects\universal\refract.p3d", 1, 0, 1, 0], // shape: [path, nth, row, column, loop]
        "",                              // animationName (obsolete, must be empty)
        "Billboard",                     // type
        1,                               // timerPeriod
        3,                               // lifetime
        [0, 0, 0],                       // position
        [0, 0, 0.5],                     // moveVelocity (rising heat)
        0,                               // rotationVelocity (number, rotations/s)
        1.0,                             // weight
        0.1,                             // volume
        0,                               // rubbing
        [_size, _size * 1.5],            // size progression (array of numbers)
        [[1, 1, 1, _alpha], [1, 1, 1, _alpha * 0.3], [1, 1, 1, 0]], // colour fade (array of RGBA)
        [1000],                          // animationPhase (array of numbers)
        1,                               // randomDirectionPeriod
        1,                               // randomDirectionIntensity
        "",                              // onTimer script
        "",                              // beforeDestroy script
        _player,                         // object to attach
        0,                               // angle (radians, optional)
        false,                           // onSurface (boolean, optional)
        -1                               // bounceOnSurface (number, optional, -1 = disabled)
    ];

    _mirage setParticleRandom [0, [_size, _size, 0], [0, 0, 0], 0, 0, [0, 0, 0, 0], 0, 0];
    _mirage setDropInterval (0.08 / _intensity);

    missionNamespace setVariable [QGVAR(mirageSource), _mirage];

    // Auto-cleanup when intensity drops
    [_mirage, _intensity] spawn {
        params ["_source", "_startIntensity"];
        waitUntil {
            sleep 2;
            private _cur = missionNamespace getVariable [QGVAR(mirageIntensity), 0];
            _cur < 0.02 || isNull _source || !alive _source
        };
        deleteVehicle _source;
        missionNamespace setVariable [QGVAR(mirageSource), objNull];
    };
};
