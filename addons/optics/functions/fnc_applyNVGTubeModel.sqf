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
            _hVig ppEffectAdjust [0.5, 0.5, 0, 0];
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
private _tier = "AUTO";

// Per-tier tube constants derived from measured datasheets.
//
// Sources:
//   PVS-31A: L3Harris sell sheet, Steele Industries per-tube data
//   GEN3:    Elbit MX-10160 (MIL-PRF-49428F), TNVC
//   GEN2:    Armasight PVS-7, Hamamatsu gated II handbook
//   GEN1:    Photonics Handbook, RP Photonics (literature-typical)
//
// Sensitivity = luminous gain (cd/m²/lx), midpoint of published range.
// noiseFloor = 1/SRN ratio (theoretical minimum noise, doubled for
//   dark current and MCP excess noise factor).
// snrMid = midpoint of published SNR range (ratio, not dB).
// haloDiam = halo diameter in mm on the 18mm tube face (radius = half).
//   Halo is the bright disc around a point source caused by electron
//   scattering in the MCP and phosphor bloom.
// mtf15 = MTF at 15 lp/mm (modulation transfer, 0..1).  Published for
//   GEN3 (Elbit); estimated for others from resolution and era.
// phosphorTint = [R, G, B, A] colour of the phosphor screen.
//   P43 (green): peak 545nm, relative efficiency 1.0 (Exosens phosphor guide).
//   P45 (white): ~545nm broadband, rel eff ~0.95.
//   P20 (yellow-green): older phosphor, peak ~550nm.
// chromaStrenght = lateral colour in fraction of image height.
//   NVG objectives are achromatic multi-element designs corrected for
//   600-900nm.  Residual lateral colour is ~1-2% of image height
//   between 600nm and 900nm (NBS Circular 549, Abbe numbers:
//   crown BK7 Vd=64.2, flint SF2 Vd=33.8).
// maxOutputBrightness = cd/m² of the phosphor screen at AGC clamp.
//   GEN3 P43: 9.6-14.4 cd/m² (Elbit MX-10160: 2.8-4.2 fL).
//   PVS-31A P45: 6.9-13.7 cd/m² (Elbit: 2.0-4.0 fL).
//   GEN2/GEN1: estimated from lower gain and older phosphor.
private _sensitivity = 10000;
private _noiseFloor = 0.15;
private _mtf15 = 0.45;
private _phosphorTint = [0.0, 0.9, 0.0, 0.95];
private _chromaStrength = 0.020;
private _vigStrength = [0.5, 0.5, 0.008, 0.015];
private _bloomBase = 0.15;
private _bloomScale = 0.22;
private _maxOutputCDM2 = 6;

if (_hmd find "USP_PVS31" >= 0 || _hmd find "PVS31" >= 0 || _hmd find "USP_PVS_31" >= 0) then {
    _tier = "PVS31";
    _sensitivity = 110000;
    _noiseFloor = 0.03;
    _mtf15 = 0.65;
    _phosphorTint = [0.6, 0.6, 0.8, 0.7];
    _chromaStrength = 0.003;
    _vigStrength = [0.5, 0.5, 0.003, 0.005];
    _bloomBase = 0.06;
    _bloomScale = 0.09;
    _maxOutputCDM2 = 10.3;
} else {
    if (_hmd find "NVGen3" >= 0 || _hmd find "NVGogglesB" >= 0 || _hmd find "NVGoggles_INDEP" >= 0) then {
        _tier = "GEN3";
        _sensitivity = 20000;
        _noiseFloor = 0.04;
        _mtf15 = 0.61;
        _phosphorTint = [0.0, 0.85, 0.0, 0.9];
        _chromaStrength = 0.008;
        _vigStrength = [0.5, 0.5, 0.005, 0.008];
        _bloomBase = 0.08;
        _bloomScale = 0.12;
        _maxOutputCDM2 = 12;
    } else {
        if (_hmd find "NVGen2" >= 0 || _hmd find "NVGoggles_OPFOR" >= 0) then {
            _tier = "GEN2";
            _sensitivity = 10000;
            _noiseFloor = 0.08;
            _mtf15 = 0.45;
            _phosphorTint = [0.0, 0.9, 0.0, 0.95];
            _chromaStrength = 0.020;
            _vigStrength = [0.5, 0.5, 0.008, 0.015];
            _bloomBase = 0.15;
            _bloomScale = 0.22;
            _maxOutputCDM2 = 6;
        } else {
            if (_hmd find "GEN1" >= 0 || _hmd find "NVGoggles" >= 0) then {
                _tier = "GEN1";
                _sensitivity = 1000;
                _noiseFloor = 0.15;
                _mtf15 = 0.30;
                _phosphorTint = [0.05, 0.8, 0.0, 0.85];
                _chromaStrength = 0.040;
                _vigStrength = [0.5, 0.5, 0.012, 0.025];
                _bloomBase = 0.30;
                _bloomScale = 0.35;
                _maxOutputCDM2 = 3;
            };
        };
    };
};
missionNamespace setVariable [QGVAR(nvgTubeTier), _tier];

// ─── Ambient light in lux ────────────────────────────────────────────────
// moonIntensity 0 = starlight (~0.001 lux), 1 = full moon (~0.25 lux).
// Linear approximation adequate for the NVG operating range.
private _lux = 0.001 + _moonLight * 0.249;

// ─── Gain (automatic gain control) ───────────────────────────────────────
// Real AGC clamps output brightness at MOB (maximum output brightness)
// across a ~20:1 input range (Elbit MX-10160: 2.8-4.2 fL held across
// 1-20 fc input).  Gain is inversely proportional to input illuminance
// until the AGC clamp engages.
//
// Formula: gain = sensitivity / (lux + 1).  At starlight (0.001 lux),
// gain ≈ sensitivity.  At full moon (0.25 lux), gain ≈ sensitivity/1.25.
// The real tube's AGC reduces gain ~4× over 100× input rise; this
// formula produces a similar ~2.5× reduction over the 250× input range.
private _gain = _sensitivity / (_lux + 1);
private _maxGain = _sensitivity;
_gain = _gain min _maxGain;
missionNamespace setVariable [QGVAR(nvgGain), _gain];

// ─── Shot noise (Poisson photon statistics) ──────────────────────────────
// Photon arrival follows Poisson statistics: SNR = √N where N is the
// number of detected photons.  At starlight, N is small and shot noise
// dominates.  At full moon, N is large and the noise floor (dark current
// + MCP excess noise) dominates.
//
// noiseFloor = 1/SNR_mid × 2 (doubled for MCP excess noise factor,
// typically 1.2-1.5 for Gen 3, higher for Gen 1/2 without ion barrier).
// The noise floor represents the irreducible noise at full moonlight.
private _photonCount = _lux * _sensitivity;
private _shotNoise = 1 / sqrt(_photonCount + 1);
private _noise = _noiseFloor + (1 - _noiseFloor) * _shotNoise;
_noise = 0.03 max _noise min 1;
missionNamespace setVariable [QGVAR(nvgNoise), _noise];

// ─── Bloom (bright-source halos scale with ambient light) ────────────────
// Halo diameter is a fixed physical property of the tube (0.7-1.0mm for
// Gen 3, measured on the 18mm tube face).  The DynamicBlur effect
// simulates the visual impact of these halos, which scale with scene
// brightness.  At starlight, halos are less visible (dark scene).  At
// full moon, brighter sources produce more noticeable blooming.
private _bloom = _bloomBase + _bloomScale * (_moonLight / 1.0);
_bloom = 0 max _bloom min 1;

// ─── Brightness (AGC-clamped output) ─────────────────────────────────────
// Real NVGs clamp output brightness at MOB (maximum output brightness).
// Elbit MX-10160: output held at 2.8-4.2 fL (9.6-14.4 cd/m²) across
// 1-20 fc input.  Photonis 4G+: MOB 4-17 cd/m².
//
// The ppEffect brightness scales from dim (starlight) to _maxOutputCDM2
// (full moon), then clamps.  This produces the realistic AGC behaviour
// where the NVG image gets slightly brighter with more ambient light,
// but never becomes "bright" — NVGs are dim devices.
private _brightness = _maxOutputCDM2 / 25 * (0.6 + 0.4 * _moonLight);

// ─── FilmGrain parameters (shot noise) ───────────────────────────────────
// Grain sharpness and size scale with noise level.  At high noise
// (starlight), grain is coarse and sharp.  At low noise (full moon),
// grain is fine and soft.  Monochromatic = 1 (grayscale grain for
// P45 white phosphor; P43 green also uses grayscale for realism).
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
// Lateral colour from residual dispersion in the objective lens.
// NVG objectives are achromatic multi-element designs corrected for
// 600-900nm (BK7 crown Vd=64.2, SF2 flint Vd=33.8).  Residual
// lateral colour is ~1-2% of image height (NBS Circular 549).
// _chromaStrenght is the fraction of image height for the colour fringing.
_hChroma ppEffectAdjust [_chromaStrength, _chromaStrength, false];
_hChroma ppEffectEnable true;
_hChroma ppEffectForceInNVG true;
_hChroma ppEffectCommit 0;

// ─── ColorCorrections (phosphor tint + brightness + contrast) ───────────
// Params: [brightness, contrast, offset, blend, colorize, weight]
//
// brightness: AGC-clamped output (dim; NVGs are not bright devices).
// contrast: MTF at 15 lp/mm.  GEN3 P43: 61% (Elbit MX-10160).
//   PVS-31A: ~65% (estimated from 64-81 lp/mm resolution).
//   GEN2: ~45% (estimated from 47-54 lp/mm).
//   GEN1: ~30% (estimated from 30-40 lp/mm).
// colorize: phosphor screen tint.  P43 peak 545nm (green).
//   P45 broadband ~545nm (white with blue component).
//   P20 peak ~550nm (yellow-green).
_hCC ppEffectAdjust [_brightness, _mtf15, 0, [0,0,0,0], _phosphorTint, [0,0,0,0]];
_hCC ppEffectEnable true;
_hCC ppEffectForceInNVG true;
_hCC ppEffectCommit 0;

// ─── DynamicBlur (blooming / halos from bright sources) ──────────────────
_hBloom ppEffectAdjust [_bloom];
_hBloom ppEffectEnable true;
_hBloom ppEffectForceInNVG true;
_hBloom ppEffectCommit 0;

// ─── RadialBlur (optical edge degradation) ───────────────────────────────
// NVG optics are sharpest at centre, softest at edges.  MTF drops
// toward the edge of the 40° FOV.  This simulates the fixed-focus
// depth-of-field of NVG objectives (focused at ~10-15m, objects
// beyond ~15m are progressively softer).
// _vigStrength = [centerX, centerY, blurX, blurY, blurScale]
_hVig ppEffectAdjust _vigStrength;
_hVig ppEffectEnable true;
_hVig ppEffectForceInNVG true;
_hVig ppEffectCommit 0;

// ─── FilmGrain (shot noise - the NVG aesthetic) ──────────────────────────
_hGrain ppEffectAdjust [_noise, _sharpness, _grainSize, 0.5, 1.0, 1];
_hGrain ppEffectEnable true;
_hGrain ppEffectForceInNVG true;
_hGrain ppEffectCommit 0;
missionNamespace setVariable [QGVAR(nvgGrainActive), true];
