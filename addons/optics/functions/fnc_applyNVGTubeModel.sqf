#include "..\script_component.hpp"

/*
NVG tube model — physics-coupled image-intensifier behaviour for the
NVG view (vision mode 1).

Architecture: recreate ALL ppEffect handles every tick. This matches
ACE3's pattern (addons/nightvision/functions/fnc_pfeh.sqf). Arma 3
kills ppEffects on alt-tab, resize, AT sights. Without recreation
the effects stay dead. ACE3's comment: "This is hacky but... works."

Model chain: moonIntensity -> gain -> shot noise -> five
post-process effects forced into the NVG view:

  ChromAberration  - optical imperfection (lens dispersion)
  ColorCorrections - phosphor tint, brightness, contrast
  DynamicBlur      - blooming / halos from bright sources
  RadialBlur       - optical edge degradation
  FilmGrain        - shot noise (inverse light)

Light source: moonIntensity (engine variable, 0..1 moon phase).
Overcast and rain subtract from this. This is the same variable
ACE3 uses. ambientLux is NOT used for NVG — it can be 0 or
unpopulated when the NVG tick fires.

Gate:    vision mode 1
Reads:   moonIntensity, overcast, rain, hmd _player
Sets:    QGVAR(nvgGain), QGVAR(nvgNoise), QGVAR(nvgTubeTier),
         QGVAR(nvgGrainActive), five ppEffects (client-side only)
*/

private _player = call CBA_fnc_currentUnit;
if (isNil "_player" || !alive _player || cameraOn != _player) exitWith {};

// Vision modes verified in-game: 0 = normal, 1 = NVG, 2 = thermal.
// The tube model runs only in NVG.  Leaving NVG fades every NVG effect
// to a neutral state and disables it.
if (currentVisionMode _player != 1) exitWith {
    private _active = missionNamespace getVariable [QGVAR(nvgGrainActive), false];
    if (_active) then {
        // ChromAberration is a shared handle (owned by managePostProcess in
        // normal mode).  Fade it to neutral here so it does not linger into
        // thermal; managePostProcess re-owns it in normal mode.
        private _hChroma = missionNamespace getVariable [QGVAR(ppHandle_ChromAberration), -1];
        if (_hChroma >= 0) then {
            _hChroma ppEffectAdjust [0, 0, false];
            _hChroma ppEffectCommit 1;
        };

        private _hCC = missionNamespace getVariable [QGVAR(ppHandle_NVG_CC), -1];
        if (_hCC >= 0) then {
            _hCC ppEffectAdjust [1, 1, 0, [0,0,0,0], [1,1,1,1], [0,0,0,0]];
            _hCC ppEffectCommit 1.5;
        };
        [{
            (missionNamespace getVariable [QGVAR(ppHandle_NVG_CC), -1]) ppEffectEnable false;
        }, [], 2] call CBA_fnc_waitAndExecute;

        private _hBloom = missionNamespace getVariable [QGVAR(ppHandle_NVG_Bloom), -1];
        if (_hBloom >= 0) then {
            _hBloom ppEffectAdjust [0];
            _hBloom ppEffectCommit 1;
        };
        [{
            (missionNamespace getVariable [QGVAR(ppHandle_NVG_Bloom), -1]) ppEffectEnable false;
        }, [], 1.5] call CBA_fnc_waitAndExecute;

        private _hVig = missionNamespace getVariable [QGVAR(ppHandle_NVG_Vignette), -1];
        if (_hVig >= 0) then {
            _hVig ppEffectAdjust [0.5, 0.5, 0, 0, 0];
            _hVig ppEffectCommit 1;
        };
        [{
            (missionNamespace getVariable [QGVAR(ppHandle_NVG_Vignette), -1]) ppEffectEnable false;
        }, [], 1.5] call CBA_fnc_waitAndExecute;

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
    // Clear stale tube state so diagnostics and scripts do not read
    // values from a previous NVG session.
    missionNamespace setVariable [QGVAR(nvgTubeTier), "NONE"];
    missionNamespace setVariable [QGVAR(nvgGain), 0];
    missionNamespace setVariable [QGVAR(nvgNoise), 0];
};

// ─── Ambient light input ─────────────────────────────────────────────────
// moonIntensity: engine variable, 0..1 based on moon phase.
// Same source ACE3 uses. Subtracts overcast and rain.
private _moonLight = 0 max (moonIntensity - ((overcast * .8) min .275) - (rain * .5));

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

// ─── Per-tier tube constants ─────────────────────────────────────────────
// AUTO falls back to the Gen 2 tube (the existing default).
private _ccBrightness = 0.58;
private _ccContrast = 0.72;
private _colorize = [0.0, 0.28, 0.0, 0.52];
private _contrastRGB = [0.82, 1.12, 0.82, 1.0];
private _bloomBase = 0.25;
private _bloomScale = 0.20;
private _chroma = [0.018, 0.018, false];
private _vig = [0.5, 0.5, 0.008, 0.008, 0.015];

switch (_tier) do {
    case "PVS31": {
        _ccBrightness = 0.88;
        _ccContrast = 0.94;
        _colorize = [0.0, 0.12, 0.0, 0.28];
        _contrastRGB = [0.95, 1.05, 0.95, 1.0];
        _bloomBase = 0.04;
        _bloomScale = 0.08;
        _chroma = [0.002, 0.002, false];
        _vig = [0.5, 0.5, 0.002, 0.002, 0.004];
    };
    case "GEN3": {
        _ccBrightness = 0.78;
        _ccContrast = 0.88;
        _colorize = [0.0, 0.18, 0.0, 0.38];
        _contrastRGB = [0.90, 1.08, 0.90, 1.0];
        _bloomBase = 0.10;
        _bloomScale = 0.15;
        _chroma = [0.008, 0.008, false];
        _vig = [0.5, 0.5, 0.005, 0.005, 0.008];
    };
    case "GEN2": {
        _ccBrightness = 0.58;
        _ccContrast = 0.72;
        _colorize = [0.0, 0.28, 0.0, 0.52];
        _contrastRGB = [0.82, 1.12, 0.82, 1.0];
        _bloomBase = 0.25;
        _bloomScale = 0.20;
        _chroma = [0.018, 0.018, false];
        _vig = [0.5, 0.5, 0.008, 0.008, 0.015];
    };
    case "GEN1": {
        _ccBrightness = 0.42;
        _ccContrast = 0.58;
        _colorize = [0.0, 0.38, 0.0, 0.65];
        _contrastRGB = [0.75, 1.18, 0.75, 1.0];
        _bloomBase = 0.40;
        _bloomScale = 0.30;
        _chroma = [0.035, 0.035, false];
        _vig = [0.5, 0.5, 0.012, 0.012, 0.025];
    };
};

// ─── Gain (automatic gain control) ───────────────────────────────────────
// Gain rises as light falls.
private _gain = _sensitivity / (_moonLight * 1000 + 1);
private _maxGain = _sensitivity * 2;
_gain = _gain min _maxGain;
missionNamespace setVariable [QGVAR(nvgGain), _gain];

// ─── Shot noise (inverse light scaling - the physics core) ───────────────
// Noise is near 1.0 at near-total darkness and near _noiseFloor at full
// moonlight.
private _noise = _noiseFloor + (1 - _noiseFloor) * (0.05 / (_moonLight + 0.05));
_noise = 0.05 max _noise min 1;
missionNamespace setVariable [QGVAR(nvgNoise), _noise];

// ─── Bloom (bright-source halos scale with ambient light) ────────────────
// 1.0 is the maximum expected moonIntensity at full moon.
private _bloom = _bloomBase + _bloomScale * (_moonLight / 1.0);
_bloom = 0 max _bloom min 1;

// ─── Brightness (image brightness scales with gain) ──────────────────────
// AGC: the image brightens as light falls, up to the tier brightness.
private _brightness = _ccBrightness * (0.7 + 0.3 * (_gain / _maxGain));

// ─── FilmGrain parameters (shot noise) ───────────────────────────────────
// Higher noise gives sharper, larger grain.
private _sharpness = linearConversion [1, 0, _noise, 12, 3, true];
private _grainSize = linearConversion [1, 0, _noise, 3, 1, true];

// ─── Recreate all NVG handles every tick ─────────────────────────────────
// ACE3 pattern: ppEffectCreate each tick prevents the engine from
// killing effects on alt-tab, resize, AT sights, etc.
private _hChroma = ppEffectCreate ["ChromAberration", 3000];
private _hCC     = ppEffectCreate ["ColorCorrections", 5100];
private _hBloom  = ppEffectCreate ["DynamicBlur", 4100];
private _hVig    = ppEffectCreate ["RadialBlur", 6000];
private _hGrain  = ppEffectCreate ["FilmGrain", 1200];

// Store handles for the exit block (fade-out on leaving NVG)
missionNamespace setVariable [QGVAR(ppHandle_ChromAberration), _hChroma];
missionNamespace setVariable [QGVAR(ppHandle_NVG_CC), _hCC];
missionNamespace setVariable [QGVAR(ppHandle_NVG_Bloom), _hBloom];
missionNamespace setVariable [QGVAR(ppHandle_NVG_Vignette), _hVig];
missionNamespace setVariable [QGVAR(ppHandle_NVG_Grain), _hGrain];

// ─── ChromAberration (optical imperfection) ──────────────────────────────
_hChroma ppEffectAdjust _chroma;
_hChroma ppEffectEnable true;
_hChroma ppEffectForceInNVG true;
_hChroma ppEffectCommit 0;

// ─── ColorCorrections (phosphor tint + brightness + contrast) ───────────
// Params: [brightness(0..2), contrast(0..inf), offset, blend, colorize, weight]
_hCC ppEffectAdjust [_brightness, _ccContrast, 0, _colorize, _contrastRGB, [0,0,0,0]];
_hCC ppEffectEnable true;
_hCC ppEffectForceInNVG true;
_hCC ppEffectCommit 0;

// ─── DynamicBlur (blooming / halos from bright sources) ──────────────────
_hBloom ppEffectAdjust [_bloom];
_hBloom ppEffectEnable true;
_hBloom ppEffectForceInNVG true;
_hBloom ppEffectCommit 0;

// ─── RadialBlur (optical edge degradation) ───────────────────────────────
_hVig ppEffectAdjust _vig;
_hVig ppEffectEnable true;
_hVig ppEffectForceInNVG true;
_hVig ppEffectCommit 0;

// ─── FilmGrain (shot noise - the NVG aesthetic) ──────────────────────────
_hGrain ppEffectAdjust [_noise, _sharpness, _grainSize, 0.5, 1.0, 1];
_hGrain ppEffectEnable true;
_hGrain ppEffectForceInNVG true;
_hGrain ppEffectCommit 0;
missionNamespace setVariable [QGVAR(nvgGrainActive), true];
