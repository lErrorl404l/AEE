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
        // Destroy handles on exit and reset to -1.  The engine can kill
        // ppEffects (alt-tab, resize) leaving stale positive handle
        // numbers; those then fail every subsequent call with "Invalid
        // post effect handle".  Resetting to -1 forces a clean recreate
        // on next entry.
        {
            private _h = missionNamespace getVariable [_x, -1];
            if (_h >= 0) then {
                ppEffectDestroy _h;
                missionNamespace setVariable [_x, -1];
                private _logMsg = format ["thermal exit: destroyed %1 (was %2)", _x, _h];
                AEE_LOG_DEBUG(_logMsg);
            };
        } forEach [
            QGVAR(ppHandle_Thermal_CC),
            QGVAR(ppHandle_Thermal_Grain),
            QGVAR(ppHandle_Thermal_Blur)
        ];
        AEE_LOG_INFO("thermal effects torn down (vision mode left)");

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

// ─── Pan smear (detector readout artifact) ────────────────────────────────
// Real uncooled microbolometers have a row-by-row readout cycle.  Fast
// panning smears hot sources horizontally across detector rows.  We
// approximate this with turn-rate from the player's look direction delta.
private _prevDir = missionNamespace getVariable [QGVAR(thermalPrevDir), getDir _player];
private _dir = getDir _player;
private _dirDelta = abs (_dir - _prevDir);
if (_dirDelta > 180) then { _dirDelta = 360 - _dirDelta; };
missionNamespace setVariable [QGVAR(thermalPrevDir), _dir];
private _panSmear = if (diag_deltaTime > 0) then {
    linearConversion [0, 90, _dirDelta / diag_deltaTime, 0.0, 0.04, true]
} else { 0 };

// ─── Thermal window effects (fog/rain on lens) ────────────────────────────
// Fog scatters LWIR through Mie scattering; rain absorbs it through the
// water film on the lens.  Both degrade the thermal image by adding blur.
private _fogDensity = missionNamespace getVariable [QEGVAR(core,currentFogDensity), 0];
if !(_fogDensity isEqualType 0) then { _fogDensity = 0; };
private _windowBlur = 0;
if (_fogDensity > 0.1) then {
    _windowBlur = _windowBlur + linearConversion [0.1, 0.8, _fogDensity, 0.0, 0.2, true];
};
private _rainS = ([] call FUNC(getSmoothedWeather)) select 0;
if (_rainS > 0.1) then {
    _windowBlur = _windowBlur + linearConversion [0.1, 1.0, _rainS, 0.0, 0.15, true];
};

// ─── Thermal handles (create once, recreate only when missing) ───────────
// Same pattern as the NVG model: handles are created once on entry and
// only recreated when the engine killed them (alt-tab, resize, AT sights).
// Never on a timer — rebuilding live effects every tick leaves stale
// handles, climbs priorities, and spams "Invalid post effect handle".
// Priorities sit above the NVG handles so the two never collide.
// A -1 handle (priority taken) bumps until it succeeds.
private _hCC    = missionNamespace getVariable [QGVAR(ppHandle_Thermal_CC), -1];
private _hGrain = missionNamespace getVariable [QGVAR(ppHandle_Thermal_Grain), -1];
private _hBlur  = missionNamespace getVariable [QGVAR(ppHandle_Thermal_Blur), -1];

if (_hCC < 0 || _hGrain < 0 || _hBlur < 0) then {
    {
        private _h = missionNamespace getVariable [_x, -1];
        if (_h >= 0) then {
            ppEffectDestroy _h;
            missionNamespace setVariable [_x, -1];
            private _logMsg = format ["thermal recreate: destroyed %1 (was %2)", _x, _h];
            AEE_LOG_DEBUG(_logMsg);
        };
    } forEach [
        QGVAR(ppHandle_Thermal_CC),
        QGVAR(ppHandle_Thermal_Grain),
        QGVAR(ppHandle_Thermal_Blur)
    ];

    private _handles = [];
    {
        _x params ["_name", "_priority", "_store"];
        private _handle = ppEffectCreate [_name, _priority];
        private _guard = 0;
        while {_handle < 0 && _guard < 100} do {
            _priority = _priority + 1;
            _handle = ppEffectCreate [_name, _priority];
            _guard = _guard + 1;
        };
        missionNamespace setVariable [_store, _handle];
        _handles pushBack _handle;
        private _logMsg = format ["created thermal %1 priority=%2 handle=%3", _name, _priority, _handle];
        AEE_LOG_DEBUG(_logMsg);
    } forEach [
        ["ColorCorrections", 5200, QGVAR(ppHandle_Thermal_CC)],
        ["FilmGrain",       1300, QGVAR(ppHandle_Thermal_Grain)],
        ["DynamicBlur",     4200, QGVAR(ppHandle_Thermal_Blur)]
    ];
    _handles params ["_hCC", "_hGrain", "_hBlur"];
};

// ─── ColorCorrections (display gain/contrast) ────────────────────────────
// Params: [brightness, contrast, offset, blend, colorize, weight]
//
// The ENGINE renders the native thermal image — IR radiance mapped through
// the device's own palette (white/black/green/red/orange-hot, cycled by the
// engine's TI mode key).  Our ColorCorrections is the display gain/level
// stage, like a real FLIR's manual brightness/contrast controls.  It does
// NOT recolor the palette — the native system owns that.
//
// Values match the proven A3TI mod (workshop 2041057379) THERMAL preset:
//   DEFAULT_TIPP_SETTINGS = [1.16, 0.62, 0, 0]
//   brightness 1.16 (slight boost; wiki: 0 = black, 1 = unchanged —
//     our earlier 0.57 and 0.0 both darkened the native image to black)
//   contrast 0.62 (A3TI thermal display contrast)
//   weight [1,1,1,0] = NO desaturation (A3TI).  The wiki default
//     [0.299,0.587,0.114,0] desaturates the native palette to greyscale
//     — wrong for thermal, whose colour palettes are meaningful.
//   colorize [1,1,1,0]: alpha 0 = no desaturation, native palette passes
//     through untouched.
// AGC response is applied via contrast, not brightness: poor conditions
// (rain, fog, crossover) lower contrast; clean conditions raise it.
private _brightness = 1.16;
private _ccContrast = linearConversion [1, 0, _effective, 0.62, 0.35, true];
_hCC ppEffectAdjust [_brightness, _ccContrast, 0, [0,0,0,0], [1,1,1,0], [1,1,1,0]];
_hCC ppEffectCommit 0;
_hCC ppEffectEnable true;
_hCC ppEffectForceInNVG true;

// ─── FilmGrain (sensor noise) ─────────────────────────────────────────────
// Params: [intensity, sharpness, grainSize, grainIntensity2,
//          grainIntensity3, inversion]
// Noise scales inversely with contrast: poor conditions (rain, fog,
// crossover) mean fewer usable IR photons and a noisier image.  Grain
// is coarse and sharp at high noise, fine and soft at low noise.
// Sharpness/grainSize stay near the proven A3TI values (0.75 / 1.5) and
// drift only mildly with conditions; intensity carries the signal.
private _noise     = linearConversion [1, 0, _effective, 0.05, 0.3, true];
private _sharpness = linearConversion [1, 0, _effective, 0.75, 1.5, true];
private _grainSize = linearConversion [1, 0, _effective, 1.5, 2.0, true];
_hGrain ppEffectAdjust [_noise, _sharpness, _grainSize, 0.5, 1.0, 0];
_hGrain ppEffectCommit 0;
_hGrain ppEffectEnable true;
_hGrain ppEffectForceInNVG true;

// ─── DynamicBlur (IR scatter) ─────────────────────────────────────────────
// Rain scatters and fog absorbs LWIR, smearing the image.  At crossover
// the mushy uniform scene adds to the blur.  Clean conditions: no blur.
// Ceiling kept LOW: DynamicBlur at 0.2+ reads as dimming/flicker because
// the engine re-renders the native thermal frame underneath, and the
// blur gate oscillates with mouse micro-movement.
private _blur = linearConversion [1, 0, _effective, 0.0, 0.15, true];
_blur = (_blur + _panSmear + _windowBlur) min 0.25;
_hBlur ppEffectAdjust [_blur];
_hBlur ppEffectCommit 0;
_hBlur ppEffectEnable true;
_hBlur ppEffectForceInNVG true;

// Diagnostics: set aee_optics_nvgDebug = true in the debug console to log
// every thermal tick's handles and params to the .rpt.
if (missionNamespace getVariable [QGVAR(nvgDebug), false]) then {
    diag_log text format [
        "[AEE] Thermal tick | visMode=%1 contrast=%2 crossover=%3 | handles CC=%4 grain=%5 blur=%6 | CC params %7 | grain=%8 blur=%9",
        currentVisionMode _player,
        _contrast,
        _crossover,
        _hCC,
        _hGrain,
        _hBlur,
        [_brightness, _ccContrast, 0, [0,0,0,0], [1,1,1,0], [1,1,1,0]],
        [_noise, _sharpness, _grainSize, 0.5, 1.0, 0],
        _blur
    ];
};

// ─── Eye accommodation (exposure) ───────────────────────────────────────
// Same as the NVG objective: setAperture is light intake (eye
// accommodation), not DoF.  Fixed night exposure — the sensor's output
// display brightness is constant, so the eye's accommodation is too.
// A3TI-proven night value 15; -1 restores the engine default.
setAperture 15;

missionNamespace setVariable [QGVAR(thermalActive), true];
