#include "..\script_component.hpp"

/*
Thermal vision model — physics-coupled FLIR behaviour for the thermal
view (vision mode 2).

Architecture: recreate ALL ppEffect handles every tick. This matches
ACE3's pattern (addons/nightvision/functions/fnc_pfeh.sqf). Arma 3
kills ppEffects on alt-tab, resize, AT sights. Without recreation
the effects stay dead. ACE3's comment: "This is hacky but... works."

Physics: FLIR/thermal cameras image long-wave infrared (8-14 µm LWIR).
Thermal contrast is the normalised object-background temperature gap:

    contrast = |T_object - T_background| / T_background

The engine renders white-hot/black-hot natively. This function adds
the environmental degradation the engine does not model:

  ColorCorrections - brightness, contrast, display tint
  FilmGrain        - sensor noise (scales with poor conditions)
  DynamicBlur      - IR scatter in rain/fog, mushy crossover image

Contrast input: GVAR(currentThermalContrast) (0-1) from
fnc_calculateThermalContrast.  Heat (>35 °C), rain and fog degrade it;
cold (<5 °C) boosts it.  At thermal crossover (ΔT < 1.5 °C, air ≈
surface) EGVAR(core,thermalCrossoverActive) nullifies it: the image
becomes a flat grey — AGC cannot create contrast that does not exist.

Gate:    vision mode 2
Reads:   GVAR(currentThermalContrast), EGVAR(core,thermalCrossoverActive)
Sets:    QGVAR(thermalActive), three ppEffects (client-side only)
*/

private _player = call CBA_fnc_currentUnit;
if (isNil "_player" || !alive _player || cameraOn != _player) exitWith {};

// Vision modes verified in-game: 0 = normal, 1 = NVG, 2 = thermal.
// The thermal model runs only in thermal.  Leaving thermal fades every
// thermal effect to a neutral state and disables it.
if (currentVisionMode _player != 2) exitWith {
    private _active = missionNamespace getVariable [QGVAR(thermalActive), false];
    if (_active) then {
        private _hCC = missionNamespace getVariable [QGVAR(ppHandle_Thermal_CC), -1];
        if (_hCC >= 0) then {
            _hCC ppEffectAdjust [1, 1, 0, [0,0,0,0], [1,1,1,1], [0,0,0,0]];
            _hCC ppEffectCommit 1;
        };
        [{
            (missionNamespace getVariable [QGVAR(ppHandle_Thermal_CC), -1]) ppEffectEnable false;
        }, [], 2] call CBA_fnc_waitAndExecute;

        private _hGrain = missionNamespace getVariable [QGVAR(ppHandle_Thermal_Grain), -1];
        if (_hGrain >= 0) then {
            _hGrain ppEffectAdjust [0.01, 0.1, 0.5, 0.1, 0.1, 1];
            _hGrain ppEffectCommit 1;
        };
        [{
            (missionNamespace getVariable [QGVAR(ppHandle_Thermal_Grain), -1]) ppEffectEnable false;
        }, [], 1.5] call CBA_fnc_waitAndExecute;

        private _hBlur = missionNamespace getVariable [QGVAR(ppHandle_Thermal_Blur), -1];
        if (_hBlur >= 0) then {
            _hBlur ppEffectAdjust [0];
            _hBlur ppEffectCommit 1;
        };
        [{
            (missionNamespace getVariable [QGVAR(ppHandle_Thermal_Blur), -1]) ppEffectEnable false;
        }, [], 1.5] call CBA_fnc_waitAndExecute;

        missionNamespace setVariable [QGVAR(thermalActive), false];
    };
};

// ─── Effective contrast ───────────────────────────────────────────────────
// Defensive: a nil or non-numeric stored contrast (bad variable state)
// must not propagate into ppEffectAdjust — "Type Number, expected Number"
// otherwise fires every tick.  Default to full contrast.
private _contrast = missionNamespace getVariable [QGVAR(currentThermalContrast), 1];
if !(_contrast isEqualType 0) then { _contrast = 1; };
_contrast = 0 max _contrast min 1;

// At thermal crossover (ΔT < 1.5 °C) the object-background gradient
// vanishes.  The image becomes a uniform grey — not black, the sensor
// still sees a flat scene.  Floor at 0.05 keeps a faint image.
private _crossover = missionNamespace getVariable [QEGVAR(core,thermalCrossoverActive), false];
private _effective = [_contrast, 0.05] select _crossover;

// ─── Recreate all thermal handles every tick ──────────────────────────────
// ACE3 pattern: ppEffectCreate each tick prevents the engine from
// killing effects on alt-tab, resize, AT sights, etc.  Priorities sit
// above the NVG handles (5100/1200/4100) so the two never collide.
// A -1 handle (priority taken) bumps until it succeeds.
private _handles = [];
{
    _x params ["_name", "_priority"];
    private _handle = ppEffectCreate [_name, _priority];
    private _guard = 0;
    while {_handle < 0 && _guard < 100} do {
        _priority = _priority + 1;
        _handle = ppEffectCreate [_name, _priority];
        _guard = _guard + 1;
    };
    _handles pushBack _handle;
} forEach [
    ["ColorCorrections", 5200],
    ["FilmGrain", 1300],
    ["DynamicBlur", 4200]
];
_handles params ["_hCC", "_hGrain", "_hBlur"];

// Store handles for the exit block (fade-out on leaving thermal)
missionNamespace setVariable [QGVAR(ppHandle_Thermal_CC), _hCC];
missionNamespace setVariable [QGVAR(ppHandle_Thermal_Grain), _hGrain];
missionNamespace setVariable [QGVAR(ppHandle_Thermal_Blur), _hBlur];

// ─── ColorCorrections (brightness, contrast, display tint) ────────────────
// Params: [brightness, contrast, offset, blend, colorize, weight]
//
// brightness: AGC-clamped output.  Poor contrast = dim image (the
//   sensor has little signal to amplify).
// contrast:   low contrast = washed-out image.  At crossover the scene
//   is nearly uniform, so contrast collapses toward flat grey.
// colorize:   warm-white display tint (white-hot FLIR look).  The
//   weight drops with contrast, draining the image to neutral grey.
private _brightness = linearConversion [1, 0, _effective, 1.0, 0.55, true];
private _ccContrast = linearConversion [1, 0, _effective, 1.15, 0.35, true];
private _tintWeight = linearConversion [1, 0, _effective, 0.65, 0.1, true];
_hCC ppEffectAdjust [_brightness, _ccContrast, 0, [0,0,0,0], [0.95, 0.9, 0.8, 1], _tintWeight];
_hCC ppEffectEnable true;
_hCC ppEffectForceInNVG false;
_hCC ppEffectCommit 0;

// ─── FilmGrain (sensor noise) ─────────────────────────────────────────────
// Params: [intensity, sharpness, grainSize, grainIntensity2,
//          grainIntensity3, inversion]
// Noise scales inversely with contrast: poor conditions (rain, fog,
// crossover) mean fewer usable IR photons and a noisier image.  Grain
// is coarse and sharp at high noise, fine and soft at low noise.
private _noise     = linearConversion [1, 0, _effective, 0.08, 0.6, true];
private _sharpness = linearConversion [1, 0, _effective, 3, 10, true];
private _grainSize = linearConversion [1, 0, _effective, 1, 2.5, true];
_hGrain ppEffectAdjust [_noise, _sharpness, _grainSize, 0.5, 1.0, 1];
_hGrain ppEffectEnable true;
_hGrain ppEffectForceInNVG false;
_hGrain ppEffectCommit 0;

// ─── DynamicBlur (IR scatter) ─────────────────────────────────────────────
// Rain scatters and fog absorbs LWIR, smearing the image.  At crossover
// the mushy uniform scene adds to the blur.  Clean conditions: no blur.
private _blur = linearConversion [1, 0, _effective, 0.0, 0.35, true];
_hBlur ppEffectAdjust [_blur];
_hBlur ppEffectEnable true;
_hBlur ppEffectForceInNVG false;
_hBlur ppEffectCommit 0;

missionNamespace setVariable [QGVAR(thermalActive), true];
