#include "..\script_component.hpp"

/*
Vehicle dust kickup effect — per-tick drop particles at wheel positions.

Gate:  GVAR(enabled) && player is driver of a vehicle moving > 5 km/h
Reads: GVAR(dustSuppression), GVAR(groundState), engine wind vector
Emits: `drop`-based billboard particles at each wheel position, coloured by
       ground state, alpha scaled by dust suppression factor.
*/

if (!EGVAR(core,enabled)) exitWith {};

private _player = call CBA_fnc_currentUnit;
if (isNil "_player" || !alive _player) exitWith {};

private _veh = vehicle _player;
if (_veh == _player) exitWith {};
if (_player != driver _veh) exitWith {};

private _dustSuppression = missionNamespace getVariable [QEGVAR(core,dustSuppression), 0.5];
if (_dustSuppression < 0.05) exitWith {};

private _speed = speed _veh;
if (_speed < 5) exitWith {};

private _groundState = missionNamespace getVariable [QEGVAR(core,groundState), "Normal"];
private _windArr = missionNamespace getVariable [QEGVAR(core,currentWind), wind];
private _windX = (_windArr select 0) * 0.5;

// ─── Colour palette by ground state ─────────────────────────────────────
// Alpha is weighted by dustSuppression (1 = no suppression = full dust).
private _startColor = [0.7, 0.6, 0.4, 0.3 * _dustSuppression];
private _endColor   = [0.7, 0.6, 0.4, 0.1 * _dustSuppression];

switch (_groundState) do {
    case "Mud": {
        _startColor = [0.4, 0.3, 0.2, 0.4 * _dustSuppression];
        _endColor   = [0.4, 0.3, 0.2, 0.15 * _dustSuppression];
    };
    case "Snow": {
        _startColor = [1, 1, 1, 0.3 * _dustSuppression];
        _endColor   = [1, 1, 1, 0.1 * _dustSuppression];
    };
    case "Dusty": {
        _startColor = [0.8, 0.7, 0.5, 0.5 * _dustSuppression];
        _endColor   = [0.8, 0.7, 0.5, 0.2 * _dustSuppression];
    };
};

// ─── Gather wheel positions (model-space) ───────────────────────────────
private _wheelPositions = [];
for "_axle" from 0 to 4 do {
    for "_side" from 1 to 2 do {
        private _sel = format ["wheel_%1_%2_geometry", _axle, _side];
        private _pos = _veh selectionPosition _sel;
        if (_pos isNotEqualTo [0, 0, 0]) then {
            _wheelPositions pushBack _pos;
        };
    };
};

if (_wheelPositions isEqualTo []) exitWith {};

// ─── Emit particles ─────────────────────────────────────────────────────
{
    drop [
        "\A3\data_f\ParticleEffects\Universal\Universal.p3d",
        "Billboard",
        0.1,                                 // timer period
        0.5 + random 0.5,                    // life
        _x,                                  // model-space pos (attached to _veh)
        [
            -_windX + random 0.5 - 0.25,
            random 0.5 - 0.25,
            -0.1 - random 0.3
        ],                                   // velocity
        0,                                   // weight
        1,                                   // volume
        0,                                   // rubbing
        [0.2, 0.5, 1],                      // size
        [_startColor, _endColor],            // colour
        [0.5],                               // animation phase
        0,                                   // random dir period
        0.5,                                 // random dir intensity
        "",                                  // on surface
        "",                                  // before destroy
        _veh                                 // attach to
    ];
} forEach _wheelPositions;
