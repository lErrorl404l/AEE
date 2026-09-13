#include "..\script_component.hpp"

/*
NVG tube model - physics-coupled image-intensifier behaviour for the
NVG view (vision mode 1).

Model chain: ambient lux -> gain -> shot noise (inverse light) -> FilmGrain
forced into the NVG view, tiered by HMD classname.

The engine suppresses post-process effects in NVG by default.  To render
grain INSIDE the NVG view, create the effect, adjust it, and mark it
ppEffectForceInNVG true.  ACE3 uses this pattern in
addons/nightvision/functions/fnc_pfeh.sqf.

Gate:    EGVAR(core,opticsEnabled) && vision mode 1
Reads:   QEGVAR(environmental,ambientLux), hmd _player
Sets:    QGVAR(nvgGain), QGVAR(nvgNoise), QGVAR(nvgTubeTier),
         FilmGrain ppEffect (client-side only)
*/

if (!EGVAR(core,opticsEnabled)) exitWith {};

private _player = call CBA_fnc_currentUnit;
if (isNil "_player" || !alive _player || cameraOn != _player) exitWith {};

// Vision modes verified in-game: 0 = normal, 1 = NVG, 2 = thermal.
// The tube model runs only in NVG.  Leaving NVG fades the grain to a
// neutral state and disables the effect.
if (currentVisionMode _player != 1) exitWith {
    private _active = missionNamespace getVariable [QGVAR(nvgGrainActive), false];
    if (_active) then {
        private _hGrain = missionNamespace getVariable [QGVAR(ppHandle_NVG_Grain), -1];
        if (_hGrain >= 0) then {
            _hGrain ppEffectAdjust [0.01, 0.1, 0.5, 0.1, 0.1, 1];
            _hGrain ppEffectCommit 1;
        };
        [{
            (missionNamespace getVariable [QGVAR(ppHandle_NVG_Grain), -1]) ppEffectEnable false;
        }, [], 1.5] call CBA_fnc_waitAndExecute;
        missionNamespace setVariable [QGVAR(nvgGrainActive), false];
    };
};

// ─── Ambient light input ─────────────────────────────────────────────────
private _lux = missionNamespace getVariable [QEGVAR(environmental,ambientLux), 0.05];
_lux = 0.0005 max _lux min 0.5;

// ─── Tube tier by HMD classname ──────────────────────────────────────────
// Substring tests run most-specific first.  "NVGoggles" is a substring of
// "NVGoggles_OPFOR", "NVGogglesB_*" and "NVGoggles_INDEP".  The broad
// Gen 1 test must come last or it swallows every other tier.
private _hmd = hmd _player;
private _sensitivity = 1200;
private _noiseFloor = 0.20;
private _tier = "AUTO";

if (_hmd find "USP_PVS31" >= 0 || _hmd find "PVS31" >= 0 || _hmd find "USP_PVS_31" >= 0) then {
    _sensitivity = 2500;
    _noiseFloor = 0.06;
    _tier = "PVS31";
} else {
    if (_hmd find "NVGen3" >= 0 || _hmd find "NVGogglesB" >= 0 || _hmd find "NVGoggles_INDEP" >= 0) then {
        _sensitivity = 1800;
        _noiseFloor = 0.10;
        _tier = "GEN3";
    } else {
        if (_hmd find "NVGen2" >= 0 || _hmd find "NVGoggles_OPFOR" >= 0) then {
            _sensitivity = 1200;
            _noiseFloor = 0.20;
            _tier = "GEN2";
        } else {
            if (_hmd find "GEN1" >= 0 || _hmd find "NVGoggles" >= 0) then {
                _sensitivity = 800;
                _noiseFloor = 0.35;
                _tier = "GEN1";
            };
        };
    };
};
missionNamespace setVariable [QGVAR(nvgTubeTier), _tier];

// ─── Gain (automatic gain control) ───────────────────────────────────────
// Gain rises as light falls.
private _gain = _sensitivity / (_lux * 1000 + 1);
private _maxGain = _sensitivity * 2;
_gain = _gain min _maxGain;
missionNamespace setVariable [QGVAR(nvgGain), _gain];

// ─── Shot noise (inverse light scaling - the physics core) ───────────────
// Noise is near 1.0 at near-total darkness and near _noiseFloor at full
// moonlight.
private _noise = _noiseFloor + (1 - _noiseFloor) * (0.05 / (_lux + 0.05));
_noise = 0.05 max _noise min 1;
missionNamespace setVariable [QGVAR(nvgNoise), _noise];

// ─── Brightness (image brightness scales with gain) ──────────────────────
private _brightness = linearConversion [_sensitivity * 0.5, _sensitivity * 2, _gain, 0.5, 1.2, true];
_brightness = 0.5 max _brightness min 1.2;

// ─── FilmGrain application (the NVG aesthetic) ───────────────────────────
// Higher noise gives sharper, larger grain.
private _sharpness = linearConversion [1, 0, _noise, 12, 3, true];
private _grainSize = linearConversion [1, 0, _noise, 3, 1, true];

private _hGrain = missionNamespace getVariable [QGVAR(ppHandle_NVG_Grain), -1];
if (_hGrain < 0) exitWith {};

_hGrain ppEffectEnable true;
_hGrain ppEffectForceInNVG true;               // render inside the NVG view
_hGrain ppEffectAdjust [_noise, _sharpness, _grainSize, 0.5, 1.0, 1];
_hGrain ppEffectCommit 0.5;
missionNamespace setVariable [QGVAR(nvgGrainActive), true];
