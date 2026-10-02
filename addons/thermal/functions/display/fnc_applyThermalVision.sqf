#include "..\..\script_component.hpp"

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

private _perfT0 = diag_tickTime;
private _player = call CBA_fnc_currentUnit;
// Run in the player's own view: on foot (cameraOn == player) or in
// the player's vehicle (pilot/passenger/gunner - cameraOn is the
// vehicle).  Skip spectator/UAV-terminal/external cameras.
private _veh = vehicle _player;
if (isNil "_player" || !alive _player) exitWith {};
if (cameraOn != _player && {cameraOn != _veh}) exitWith {};

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
            QGVAR(ppHandle_Thermal_Vignette),
            QGVAR(ppHandle_Thermal_CC),
            QGVAR(ppHandle_Thermal_Grain),
            QGVAR(ppHandle_Thermal_Blur),
            QGVAR(ppHandle_Thermal_Inversion)
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
// approximate this with turn-rate from the CAMERA look direction delta.
// The body heading (getDir) does NOT track freelook or turret traverse —
// the camera direction does.  Consume the shared eye state (the same
// screenToWorldDirection / weaponDirection source as the NVG focus) so
// freelook and vehicle turrets smear correctly.
private _eyeState = [_player] call EFUNC(core,getEyeState);
private _lookDir = _eyeState select 1;
private _prevDir = missionNamespace getVariable [QGVAR(thermalPrevDir), _lookDir];
private _dir = _lookDir;
private _dirDelta = _prevDir vectorDotProduct _dir;
_dirDelta = ((_dirDelta max -1) min 1);
_dirDelta = acos _dirDelta;   // angular change in degrees
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
private _rainS = ([] call EFUNC(core,getSmoothedWeather)) select 0;
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
private _hVig   = missionNamespace getVariable [QGVAR(ppHandle_Thermal_Vignette), -1];
private _hCC    = missionNamespace getVariable [QGVAR(ppHandle_Thermal_CC), -1];
private _hGrain = missionNamespace getVariable [QGVAR(ppHandle_Thermal_Grain), -1];
private _hBlur  = missionNamespace getVariable [QGVAR(ppHandle_Thermal_Blur), -1];
private _hInv   = missionNamespace getVariable [QGVAR(ppHandle_Thermal_Inversion), -1];

if (_hVig < 0 || _hCC < 0 || _hGrain < 0 || _hBlur < 0 || _hInv < 0) then {
    // A fresh effect must always receive its parameters, even when the engine
    // hands back a handle NUMBER it used earlier.  Clearing here is the one
    // choke point every new effect passes through, because each destroy path
    // resets its handle to -1 and the test above then recreates it.
    missionNamespace setVariable [QGVAR(ppLastParams), createHashMap];

    {
        private _h = missionNamespace getVariable [_x, -1];
        if (_h >= 0) then {
            ppEffectDestroy _h;
            missionNamespace setVariable [_x, -1];
            private _logMsg = format ["thermal recreate: destroyed %1 (was %2)", _x, _h];
            AEE_LOG_DEBUG(_logMsg);
        };
    } forEach [
        QGVAR(ppHandle_Thermal_Vignette),
        QGVAR(ppHandle_Thermal_CC),
        QGVAR(ppHandle_Thermal_Grain),
        QGVAR(ppHandle_Thermal_Blur),
        QGVAR(ppHandle_Thermal_Inversion)
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
        ["RadialBlur",      1300, QGVAR(ppHandle_Thermal_Vignette)],
        ["DynamicBlur",     4200, QGVAR(ppHandle_Thermal_Blur)],
        ["FilmGrain",       6500, QGVAR(ppHandle_Thermal_Grain)],
        ["ColorCorrections", 5200, QGVAR(ppHandle_Thermal_CC)],
        // ColorInversion: the proven BHOT mechanism (A3TI 2501, MKK 2510,
        // workshop 2041057379 / 3753145363).  Inverts the WHOLE rendered
        // frame - hot becomes black, cold becomes white - which the old
        // `_b = 1-_b` band flip never achieved for StageTI-baked objects.
        // Created unconditionally; enabled only when thermalPolarity == 1
        // (see the adjust section).  Priority 6600, above the thermal CC
        // (5200) so it inverts the graded image, below nothing else uses.
        ["ColorInversion", 6600, QGVAR(ppHandle_Thermal_Inversion)]
    ];
    _handles params ["_hVig", "_hBlur", "_hGrain", "_hCC", "_hInv"];
    private _logMsg = format ["thermal ppEffects created: vig=%1 blur=%2 grain=%3 CC=%4 inv=%5", _hVig, _hBlur, _hGrain, _hCC, _hInv];
    AEE_LOG_INFO(_logMsg);
};

// Re-read the handles from missionNamespace at FUNCTION scope.  The
// `_handles params` above runs inside the if-block, whose scope shadows
// the function-scope locals — the adjust section below would otherwise
// read stale -1 values and throw "Invalid post effect handle".  This is
// the NVG model's pattern (missionNamespace is the single source of
// truth after the create block).
_hVig   = missionNamespace getVariable [QGVAR(ppHandle_Thermal_Vignette), -1];
_hBlur  = missionNamespace getVariable [QGVAR(ppHandle_Thermal_Blur), -1];
_hGrain = missionNamespace getVariable [QGVAR(ppHandle_Thermal_Grain), -1];
_hCC    = missionNamespace getVariable [QGVAR(ppHandle_Thermal_CC), -1];
_hInv   = missionNamespace getVariable [QGVAR(ppHandle_Thermal_Inversion), -1];

// ─── Post-process kill switch (operator bisect) ───────────────────────────
// The five thermal effects are FULL-SCREEN passes (ColorCorrections,
// ColorInversion, FilmGrain, DynamicBlur, RadialBlur).  They are the only
// engine render work AEE adds in thermal beyond the engine's own thermal
// image, so this switch isolates that cost in-game with no rebuild.  With the
// setting off the handles are DISABLED (not destroyed) and the early exit
// skips every adjust/commit below, while aperture and thermalActive are still
// restored so the rest of the pipeline stays consistent.
private _ppOn = missionNamespace getVariable [QGVAR(thermalPPEffects), true];
if (!_ppOn) exitWith {
    {
        if (_x >= 0) then { _x ppEffectEnable false; };
    } forEach [_hVig, _hCC, _hGrain, _hBlur, _hInv];
    setAperture 15;
    missionNamespace setVariable [QGVAR(thermalActive), true];
    AEE_LOG_DEBUG("thermal ppEffect chain DISABLED by setting (thermalPPEffects=false)");
};

// ─── Post-process writes: change-gated ─────────────────────────────────────
// Each ppEffectAdjust followed by ppEffectCommit is an engine call into the
// render chain, and this function runs on every tick of the 0.1 s pass.  The
// vignette vector is a constant, and the grain and blur arrays move only with
// the weather.  So a write
// is issued only when the parameter array differs from the one last committed
// for that handle.  The handle is part of the cache key, so a recreated effect
// writes even when the parameters are identical.
private _ppApply = {
    params ["_hHandle", "_effectParams", "_effectOn", "_forceNVG", "_effectKey"];
    if (_hHandle < 0) exitWith {};
    private _cache = missionNamespace getVariable [QGVAR(ppLastParams), -1];
    if (_cache isEqualType 0) then {
        _cache = createHashMap;
        missionNamespace setVariable [QGVAR(ppLastParams), _cache];
    };
    private _last = _cache getOrDefault [_effectKey, []];
    if (count _last == 3) then {
        private _same = (_last select 0) isEqualTo _hHandle;
        if (_same) then { _same = (_last select 1) isEqualTo _effectParams; };
        if (_same) then { _same = (_last select 2) isEqualTo _effectOn; };
        if (_same) exitWith {};
    };
    _hHandle ppEffectAdjust _effectParams;
    _hHandle ppEffectCommit 0;
    _hHandle ppEffectEnable _effectOn;
    if (_forceNVG) then { _hHandle ppEffectForceInNVG true; };
    _cache set [_effectKey, [_hHandle, _effectParams, _effectOn]];
    missionNamespace setVariable [QGVAR(ppLastParams), _cache];
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
// The colour grade is the PROVEN A3TI WHOT spectrum (2041057379):
//   [_BRT, _CNT, 0, [0,0,0,_ALPHA], [1,1,1,_SAT], [0.33,0.33,0.33,0],
//    [0,0,0,0,0,0,4]]
// The tint is NEUTRAL GREY (0.33,0.33,0.33) - it grades the scene to
// WHOT without inverting any channel.  The 7-element blend matrix
// [0,0,0,0,0,0,4] lifts the luminance.  The OLD [3.84,-0.46,-2.72,
// -0.06] (copied from MKK) has NEGATIVE green and blue channels - it
// INVERTS those channels, so a hot barrel rendered BLACK in WHOT and
// the whole scene flipped with polarity (issue #204: 'the barrel is
// still black', 'the screen is blinding white in BHOT').  MKK's matrix
// only suits its own red-painted isotherm textures, not the engine's
// vanilla TI image.
private _brightness = 1.16;
private _ccContrast = linearConversion [1, 0, _effective, 0.62, 0.35, true];
if (_hCC >= 0) then {
        _hCC ppEffectAdjust [
            _brightness, _ccContrast, 0,
            [0, 0, 0, 0],
            [1, 1, 1, 0],
            [0.33, 0.33, 0.33, 0],
            [0, 0, 0, 0, 0, 0, 4]
        ];
        _hCC ppEffectCommit 0;
        _hCC ppEffectEnable true;
        _hCC ppEffectForceInNVG true;
    };

// ─── ColorInversion (BHOT polarity, proven mechanism) ─────────────────────
// BHOT = the SAME thermal image inverted by a ColorInversion ppEffect
// (A3TI 2501, MKK 2510).  The old `_b = 1-_b` band flip never reached
// the rendered image for StageTI-baked objects; the inversion inverts
// the actual frame.  Enabled only when thermalPolarity == 1 (black
// hot); disabled otherwise.
private _polarity = missionNamespace getVariable [QGVAR(thermalPolarity), 0];
if (!(_polarity isEqualType 0)) then { _polarity = 0; };
if (_hInv >= 0) then {
    if (_polarity == 1) then {
        _hInv ppEffectAdjust [1, 1, 1];
        _hInv ppEffectCommit 0;
        _hInv ppEffectEnable true;
        _hInv ppEffectForceInNVG true;
    } else {
        // The ACE pattern: a freshly-created ColorInversion may default
        // to ENABLED with an uninitialised (inverting) state, so
        // disabling alone does not neutralise it - adjust to the neutral
        // [0,0,0] (no inversion), commit, THEN disable.  Without this
        // the barrel rendered black-hot even with thermalPolarity 0
        // (issue #204, the 'BHOT is on but should not be' report).
        _hInv ppEffectAdjust [0, 0, 0];
        _hInv ppEffectCommit 0;
        _hInv ppEffectEnable false;
    };
};

// ─── FilmGrain (sensor noise + FPN) ───────────────────────────────────────
// Params: [intensity, sharpness, grainSize, grainIntensity2,
//          grainIntensity3, inversion]
// ONE screen-space noise source.  The environmental term scales inversely
// with contrast: poor conditions (rain, fog, crossover) mean fewer usable
// IR photons and a noisier image.  On top of it sits the detector's
// fixed-pattern noise (FPN), which is fixed to the detector ARRAY and not
// to the scene, so it belongs in screen space.  FPN amplitude is the device
// NETD over the AGC display window.  The window is carried in radiance, so
// it is converted to its equivalent temperature span through the 190 K
// full-span anchor the AGC publishes.  Row/column striping is not
// expressible in this engine (recorded in ti_fpn.rvmat).
private _envNoise = linearConversion [1, 0, _effective, 0.05, 0.3, true];
private _agcMin = missionNamespace getVariable [QGVAR(agcRadMin), -1];
private _agcMax = missionNamespace getVariable [QGVAR(agcRadMax), -1];
private _agcWindowRad = if ((_agcMin isEqualType 0) && (_agcMax isEqualType 0)) then { _agcMax - _agcMin } else { 0 };
private _agcFullSpan = missionNamespace getVariable [QGVAR(agcFullSpan), 0];
if !(_agcFullSpan isEqualType 0) then { _agcFullSpan = 0; };
private _device = [_player, vehicle _player] call EFUNC(thermal,getThermalDeviceProperties);
private _netd = _device select 0;
if !(_netd isEqualType 0) then { _netd = 0.05; };
private _fpnOn = missionNamespace getVariable [QGVAR(thermalFPN), true];
private _fpnAmp = 0;
if ((_fpnOn) && (_agcWindowRad > 0) && (_agcFullSpan > 0)) then {
    private _windowT = 190 * (_agcWindowRad / _agcFullSpan);
    if (_windowT > 0) then { _fpnAmp = _netd / _windowT; };
};
private _noise = (_envNoise + _fpnAmp) max 0 min 1;
private _sharpness = linearConversion [1, 0, _effective, 0.75, 1.5, true];
private _grainSize = linearConversion [1, 0, _effective, 1.5, 2.0, true];
if (_hGrain >= 0) then {
        [_hGrain, [_noise, _sharpness, _grainSize, 0.5, 1.0, 0], true, true, "grain"] call _ppApply;
    };

// ─── DynamicBlur (IR scatter) ─────────────────────────────────────────────
// Rain scatters and fog absorbs LWIR, smearing the image.  At crossover
// the mushy uniform scene adds to the blur.  Clean conditions: no blur.
// Ceiling kept LOW: DynamicBlur at 0.2+ reads as dimming/flicker because
// the engine re-renders the native thermal frame underneath, and the
// blur gate oscillates with mouse micro-movement.
private _blur = linearConversion [1, 0, _effective, 0.0, 0.15, true];
_blur = (_blur + _panSmear + _windowBlur) min 0.25;
if (_hBlur >= 0) then {
        [_hBlur, [_blur], true, true, "blur"] call _ppApply;
    };

// ─── RadialBlur (ocular vignette) ──────────────────────────────────────────
// Real FLIR oculars edge-darken like NVG: the objective tube vignettes the
// image.  The strength is subtle (the sensor image is far more uniform
// than an image-intensifier tube) and drifts slightly with conditions.
// Params: [blurX, blurY, offsetX, offsetY] - the NVG-model form.
private _vigStrength = [0.0040, 0.0040, 0.06, 0.06];
if (_hVig >= 0) then {
        [_hVig, _vigStrength, true, true, "vig"] call _ppApply;
    };

// Diagnostics: set aee_nightvision_nvgDebug = true in the debug console to log
// every thermal tick's handles and params to the .rpt.
if (missionNamespace getVariable [QGVAR(thermalDebug), false]
    && {currentVisionMode _player == 2}) then {
    diag_log text format [
        "[AEE] Thermal tick | visMode=%1 contrast=%2 crossover=%3 | handles CC=%4 grain=%5 blur=%6 | CC params %7 | grain=%8 blur=%9",
        currentVisionMode _player,
        _contrast,
        _crossover,
        _hCC,
        _hGrain,
        _hBlur,
        [_brightness, _ccContrast, 0, [0,0,0,0], [1,1,1,0], [0.33,0.33,0.33,0], [0,0,0,0,0,0,4]],
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
// The module trace switch, resolved once for the pass rather than
// re-expanded at the log site.
private _traceOn = AEE_TRACE_ON;
if (_traceOn) then {
    private _visMs = round ((diag_tickTime - _perfT0) * 1000);
    private _visMsg = format ["applyThermalVision %1 us | contrast %2 | fpnAmp %3 | envNoise %4 | netd %5 mK | polarity %6 | agcSpan %7",
        _visMs, _contrast, _fpnAmp, _envNoise, _netd, _polarity, _agcFullSpan];
    AEE_LOG_DEBUG(_visMsg);
};
