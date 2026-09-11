#include "..\script_component.hpp"

/*
Per-tick wind ambience — plays a short wind sound at the player's position
when wind speed exceeds a threshold.  Three tiers: gentle, moderate, gale.

Gate:  GVAR(enabled) && cameraOn == player
Reads: engine `wind` vector magnitude
*/

if (!EGVAR(core,enabled)) exitWith {};

private _player = call CBA_fnc_currentUnit;
if (isNil "_player" || !alive _player) exitWith {};
if (cameraOn != _player) exitWith {};

private _windSpeed = vectorMagnitude wind;
if (_windSpeed < 3) exitWith {};

// ─── Select sound & volume by wind tier ─────────────────────────────────
private _soundPath = "";
private _volume = 1;

switch (true) do {
    case (_windSpeed > 15): {
        _soundPath = "A3\Sounds_F\ambient\WindEnv.wss";
        _volume = (_windSpeed / 20) min 1.5;
    };
    case (_windSpeed > 8): {
        _soundPath = "A3\Sounds_F\ambient\WindEnv.wss";
        _volume = (_windSpeed / 20) min 1.2;
    };
    default {
        _soundPath = "A3\Sounds_F\ambient\WindEnv.wss";
        _volume = 0.5 + (_windSpeed / 20);
    };
};

private _pos = _player modelToWorld [0, 0, 2];
private _pitch = 0.8 + random 0.4;

playSound3D [_soundPath, objNull, false, ATLToASL _pos, _volume, _pitch, 0];
