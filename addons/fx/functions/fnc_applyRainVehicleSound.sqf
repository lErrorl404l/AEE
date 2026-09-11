#include "..\script_component.hpp"

/*
Rain-on-vehicle-roof ambience — plays a rain sound at the player's position
when they are inside a vehicle and rain exceeds a threshold.

Gate:  GVAR(enabled) && player in vehicle && rain > 0.1
Reads: engine `rain` command
*/

if (!EGVAR(core,enabled)) exitWith {};

private _player = call CBA_fnc_currentUnit;
if (isNil "_player" || !alive _player) exitWith {};

private _veh = vehicle _player;
if (_veh == _player) exitWith {};
if (rain < 0.1) exitWith {};

private _pos = _player modelToWorld [0, 0, 2];
private _volume = 1;
private _pitch = 1;
private _soundPath = "A3\Sounds_F\ambient\rain.wss";

if (rain > 0.5) then {
    _volume = 1.2;
    _pitch = 0.9 + random 0.2;
} else {
    _volume = 0.8 + random 0.4;
    _pitch = 1 + random 0.2;
};

playSound3D [_soundPath, objNull, false, ATLToASL _pos, _volume, _pitch, 0];
