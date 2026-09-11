#include "..\script_component.hpp"

/*
Breath condensation puff — visible exhalation in cold, calm air.

Reads QGVAR(currentTemperature), QGVAR(windSpeed).
Gates on GVAR(environmentalEnabled).  Creates a small white particle
cloud at the player's eye position when temp < 5 C and wind < 5 m/s.

Sets: nothing (side effect only — particle drop)
*/

if (!EGVAR(core,environmentalEnabled)) exitWith {};

private _temp      = missionNamespace getVariable [QEGVAR(core,currentTemperature), 20];
private _windSpeed = vectorMagnitude wind;

if (_temp >= 5 || _windSpeed >= 5) exitWith {};

private _player = call CBA_fnc_currentUnit;
if (isNil "_player" || !alive _player || cameraOn != _player) exitWith {};

private _headPos = eyePos _player;
drop [
    "\a3\data_f\ParticleEffects\Universal\Universal",
    0, 2,
    _headPos,
    [0, 0, 0.2],
    0, 2.5, 2, 0.2,
    [0.04, 0.12],
    [[1,1,1,0.4],[1,1,1,0.1],[1,1,1,0]],
    [0.5],
    0.1, 0.01,
    "", "",
    vehicle _player
];
