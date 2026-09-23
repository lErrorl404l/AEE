#include "..\..\script_component.hpp"

/*
Weather particle gates (issue #151) — requests to the particle pipeline.

The physics is already computed by AEE; these gates only decide which
weather phenomena are visible and hand the emission to the pipeline:

  snowfall       phase == "snow"
  blowingSnow    phase == "snow" AND wind > 10 m/s (ground-hugging)
  hail           the phase model's convective hail gate
  haboob         the #106 sandstorm intensity AND wind > 15 m/s
  hurricane      wind > 33 m/s -> the composite (rain, spray, debris)

The phase and the sandstorm intensity are the physics gates; the emission
model (fnc_particleEmission) turns them into intensity, colour and rate.
Each effect is one config row in fnc_particleEffectConfig, so this function
holds no per-effect particle data.

Gate: enabled, hasInterface, in the player's own view.
Returns: ARRAY of requests (0..5).
*/

if (!hasInterface) exitWith { [] };
if (!(missionNamespace getVariable [QEGVAR(core,enabled), true])) exitWith { [] };

private _player = call CBA_fnc_currentUnit;
private _veh = vehicle _player;
if (isNull _player || !alive _player) exitWith { [] };
if (cameraOn != _player && {cameraOn != _veh}) exitWith { [] };

private _pos = getPosASL _player;
// Use the AEE wind (terrain speed-up included) so the gate and the
// emission model read the same field; fall back to the engine vector.
private _windSpeed = missionNamespace getVariable [QEGVAR(core,currentWindStr), vectorMagnitude wind];
if !(_windSpeed isEqualType 0) then { _windSpeed = vectorMagnitude wind; };
private _phase = missionNamespace getVariable [QEGVAR(core,precipitationPhase), "rain"];
private _requests = [];

// ─── Snowfall and blowing snow ───────────────────────────────────────────
if (_phase == "snow") then {
    private _em = ["snowfall", _pos, []] call FUNC(particleEmission);
    _em params ["_intensity", "_colour", "_rate"];
    if (_intensity > 0.01) then {
        _requests pushBack createHashMapFromArray [
            ["effect", "snowfall"], ["emitter", _player], ["position", _pos],
            ["lift", 0.6], ["intensity", _intensity],
            ["colour", _colour], ["rate", _rate], ["key", "weather_snowfall"]
        ];
    };
    if (_windSpeed > 10) then {
        private _em2 = ["blowingSnow", _pos, []] call FUNC(particleEmission);
        _em2 params ["_intensity2", "_colour2", "_rate2"];
        if (_intensity2 > 0.01) then {
            _requests pushBack createHashMapFromArray [
                ["effect", "blowingSnow"], ["emitter", _player], ["position", _pos],
                ["lift", 0.6], ["intensity", _intensity2],
                ["colour", _colour2], ["rate", _rate2], ["key", "weather_blowingSnow"]
            ];
        };
    };
};

// ─── Hail ────────────────────────────────────────────────────────────────
private _em3 = ["hail", _pos, []] call FUNC(particleEmission);
_em3 params ["_intensity3", "_colour3", "_rate3"];
if (_intensity3 > 0.01) then {
    _requests pushBack createHashMapFromArray [
        ["effect", "hail"], ["emitter", _player], ["position", _pos],
        ["lift", 0.6], ["intensity", _intensity3],
        ["colour", _colour3], ["rate", _rate3], ["key", "weather_hail"]
    ];
};

// ─── Haboob ──────────────────────────────────────────────────────────────
private _sand = missionNamespace getVariable [QEGVAR(core,currentSandstorm), 0];
if !(_sand isEqualType 0) then { _sand = 0; };
if (_windSpeed > 15 && _sand > 0.05) then {
    private _em4 = ["haboob", _pos, []] call FUNC(particleEmission);
    _em4 params ["_intensity4", "_colour4", "_rate4"];
    if (_intensity4 > 0.01) then {
        _requests pushBack createHashMapFromArray [
            ["effect", "haboob"], ["emitter", _player], ["position", _pos],
            ["lift", 0.6], ["intensity", _intensity4],
            ["colour", _colour4], ["rate", _rate4], ["key", "weather_haboob"]
        ];
    };
};

// ─── Hurricane composite ─────────────────────────────────────────────────
if (_windSpeed > 33) then {
    {
        private _em5 = [_x, _pos, []] call FUNC(particleEmission);
        _em5 params ["_intensity5", "_colour5", "_rate5"];
        if (_intensity5 > 0.01) then {
            _requests pushBack createHashMapFromArray [
                ["effect", _x], ["emitter", _player], ["position", _pos],
                ["lift", 0.6], ["intensity", _intensity5],
                ["colour", _colour5], ["rate", _rate5],
                ["key", format ["weather_%1", _x]]
            ];
        };
    } forEach ["hurricane", "hurricaneSpray", "hurricaneDebris"];
};

_requests
