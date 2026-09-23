#include "..\..\script_component.hpp"

/*
Vehicle dust kickup effect — #particlesource at vehicle center with lifecycle.

Gate:  GVAR(enabled) && player is driver of a vehicle moving > 5 km/h
Reads: GVAR(dustSuppression), GVAR(groundState), engine wind vector
Emits: Billboard particles from a source attached to the vehicle,
       coloured by ground state, alpha scaled by dust suppression factor.

Uses #particlesource with lifecycle management.  Stacking guard
via QGVAR(vehicleDust) mission variable.
*/

if (!(missionNamespace getVariable [QEGVAR(core,enabled), true])) exitWith {};

private _player = call CBA_fnc_currentUnit;
if (isNil "_player" || !alive _player) exitWith {};

private _veh = vehicle _player;
if (_veh == _player) exitWith {};
if (_player != driver _veh) exitWith {};

private _dustSuppression = missionNamespace getVariable [QEGVAR(core,dustSuppression), 0.5];
if (_dustSuppression < 0.05) exitWith {};

private _intensity = missionNamespace getVariable [QGVAR(vehicleDustIntensity), 1.0];
private _density = missionNamespace getVariable [QGVAR(vehicleDustDensity), 0.08];

private _speed = speed _veh;
if (_speed < 5) exitWith {};

// Guard: skip if existing source is alive (prevents stacking)
private _existing = missionNamespace getVariable [QGVAR(vehicleDust), objNull];
if (!isNull _existing && alive _existing) exitWith {};

// Budget check: skip if over particle ceiling
if !([] call FUNC(checkParticleBudget)) exitWith {};

private _windArr = missionNamespace getVariable [QEGVAR(core,currentWind), wind];
private _windX = (_windArr select 0) * 0.5;

// ─── Surface material ────────────────────────────────────────────────────
// The map's own surface decides WHAT is kicked up: sand on sand, snow on
// snow, dirt on dirt.  The physics and the colour come from the material
// and the environmental state, not from a fixed palette.
private _pos = getPosASL _veh;
private _ground = [_pos] call FUNC(surfaceSample);
_ground params ["_material", "_groundColour", "_lift"];

// ─── State-coupled physics (issue #150) ──────────────────────────────────
// weight/volume/rubbing/bounce from the material table + AEE state:
// air density scales drag (thin air: dust travels farther), moisture
// holds the particles down, wind couples the advection.
private _physics = [_material, _lift, _groundColour, _pos] call FUNC(kickupParams);
_physics params ["_weight", "_volume", "_rubbing", "_bounce", "_matColour"];

// Alpha is weighted by dustSuppression (1 = no suppression = full dust),
// the surface lift coefficient and the vehicleDustIntensity setting.
private _alpha = _lift * _dustSuppression * _intensity;
private _startColor = [_matColour select 0, _matColour select 1, _matColour select 2, 0.45 * _alpha];
private _endColor   = [_matColour select 0, _matColour select 1, _matColour select 2, 0.15 * _alpha];

// ─── Create particle source attached to vehicle ─────────────────────────
private _source = "#particlesource" createVehicleLocal getPosASL _veh;
_source attachTo [_veh, [0, 0, 0]];
missionNamespace setVariable [QGVAR(vehicleDust), _source];
_source call FUNC(registerParticleSource);

// Circle covers the vehicle footprint (3m radius for typical vehicles)
_source setParticleCircle [3, [0, 0, 0]];
_source setParticleRandom [0.2, [3, 3, 0], [0, 0, 0], 0, 0.3, [0, 0, 0, 0], 0, 0];
_source setParticleParams [
    ["\A3\data_f\ParticleEffects\Universal\Universal.p3d", 16, 12, 9, 0], // shape: [path, nth, row, column, loop]
    "",                                      // animationName (obsolete, must be empty)
    "Billboard",                             // type
    1,                                       // timerPeriod
    0.75,                                    // lifetime (avg of 0.5-1.0)
    [0, 0, 0],                               // position (relative to vehicle)
    [-_windX + random 0.5 - 0.25, random 0.5 - 0.25, -0.2], // moveVelocity
    0,                                       // rotationVelocity (number, rotations/s)
    _weight,                                 // weight (material: dust 1.0)
    _volume,                                 // volume (drag, density-scaled)
    _rubbing,                                // rubbing (wind coupling)
    [0.2, 0.5, 1],                           // size progression (array of numbers)
    [_startColor, _endColor],                // colour progression (array of RGBA)
    [0.5],                                   // animationPhase (array of numbers)
    1,                                       // randomDirectionPeriod
    0,                                       // randomDirectionIntensity
    "",                                      // onTimer script
    "",                                      // beforeDestroy script
    _veh,                                    // object to attach
    0,                                       // angle (radians, optional)
    true,                                    // onSurface (boolean, optional)
    _bounce                                  // bounceOnSurface (number, optional)
];

// Density scales with speed (more dust at higher speeds)
private _dropInterval = linearConversion [5, 60, _speed, _density, _density / 4, true];
_source setDropInterval _dropInterval;

// ─── Auto-cleanup: delete when conditions fail ──────────────────────────
[_source, _veh] spawn {
    params ["_source", "_veh"];
    waitUntil {
        sleep 1;
        !alive _source
        || {speed _veh < 5}
        || {(call CBA_fnc_currentUnit) != driver _veh}
    };
    deleteVehicle _source;
};
