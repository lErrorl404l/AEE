#include "..\script_component.hpp"

/*
Vehicle dust kickup effect — #particlesource at vehicle center with lifecycle.

Gate:  GVAR(enabled) && player is driver of a vehicle moving > 5 km/h
Reads: GVAR(dustSuppression), GVAR(groundState), engine wind vector
Emits: Billboard particles from a source attached to the vehicle,
       coloured by ground state, alpha scaled by dust suppression factor.

Uses #particlesource with lifecycle management.  Stacking guard
via QGVAR(vehicleDust) mission variable.
*/

if (!EGVAR(core,enabled)) exitWith {};

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

private _groundState = missionNamespace getVariable [QEGVAR(core,groundState), "Normal"];
private _windArr = missionNamespace getVariable [QEGVAR(core,currentWind), wind];
private _windX = (_windArr select 0) * 0.5;

// ─── Colour palette by ground state ─────────────────────────────────────
// Alpha is weighted by dustSuppression (1 = no suppression = full dust)
// and scaled by the vehicleDustIntensity setting.
private _startColor = [0.7, 0.6, 0.4, 0.3 * _dustSuppression * _intensity];
private _endColor   = [0.7, 0.6, 0.4, 0.1 * _dustSuppression * _intensity];

switch (_groundState) do {
    case "Mud": {
        _startColor = [0.4, 0.3, 0.2, 0.4 * _dustSuppression * _intensity];
        _endColor   = [0.4, 0.3, 0.2, 0.15 * _dustSuppression * _intensity];
    };
    case "Snow": {
        _startColor = [1, 1, 1, 0.3 * _dustSuppression * _intensity];
        _endColor   = [1, 1, 1, 0.1 * _dustSuppression * _intensity];
    };
    case "Dusty": {
        _startColor = [0.8, 0.7, 0.5, 0.5 * _dustSuppression * _intensity];
        _endColor   = [0.8, 0.7, 0.5, 0.2 * _dustSuppression * _intensity];
    };
};

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
    1,                                       // weight
    0,                                       // volume
    0.5,                                     // rubbing
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
    0.5                                      // bounceOnSurface (number, optional)
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
