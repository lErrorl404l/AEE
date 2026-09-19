#include "..\..\script_component.hpp"

/*
Per-tick wind ambience — plays a wind sound at the player's position when
wind speed exceeds a threshold.  Three tiers: gentle, moderate, gale.

The vanilla wind sounds live in the Curator addon, not Sounds_F\ambient:
  a3\data_f_curator\sound\cfgsounds\wind1.wss .. wind5.wss
(verified against the BIS wiki complete sound list, Arma 2.22).  The
original code referenced A3\Sounds_F\ambient\WindEnv.wss which does not
exist — that spammed "File not found" every tick.  The tier selects a
wind file by strength.

Gate:  GVAR(enabled) && cameraOn == player
Reads: engine `wind` vector magnitude
*/

if (!EGVAR(core,enabled)) exitWith {};

private _player = call CBA_fnc_currentUnit;
if (isNil "_player" || !alive _player) exitWith {};
if (cameraOn != _player) exitWith {};

private _windSpeed = vectorMagnitude wind;
if (_windSpeed < 3) exitWith {};

private _volumeScale = missionNamespace getVariable [QGVAR(windNoiseVolume), 1.0];

// ─── Select sound & volume by wind tier ─────────────────────────────────
private _soundPath = "a3\data_f_curator\sound\cfgsounds\wind1.wss";
private _volume = 1;

switch (true) do {
    case (_windSpeed > 15): {
        _soundPath = "a3\data_f_curator\sound\cfgsounds\wind5.wss";
        _volume = ((_windSpeed / 20) min 1.5) * _volumeScale;
    };
    case (_windSpeed > 8): {
        _soundPath = "a3\data_f_curator\sound\cfgsounds\wind3.wss";
        _volume = ((_windSpeed / 20) min 1.2) * _volumeScale;
    };
    default {
        _soundPath = "a3\data_f_curator\sound\cfgsounds\wind1.wss";
        _volume = (0.5 + (_windSpeed / 20)) * _volumeScale;
    };
};

private _pos = _player modelToWorld [0, 0, 2];
private _pitch = 0.8 + random 0.4;

playSound3D [_soundPath, objNull, false, ATLToASL _pos, _volume, _pitch, 0];
