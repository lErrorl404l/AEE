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
            _hChroma ppEffectCommit 0;
        };

        // NVG effects: destroy handles on exit and reset to -1.  The engine
        // can kill ppEffects (alt-tab, resize) leaving stale positive handle
        // numbers; those then fail every subsequent call with "Invalid post
        // effect handle".  Resetting to -1 forces a clean recreate on entry.
        {
            private _h = missionNamespace getVariable [_x, -1];
            if (_h >= 0) then {
                ppEffectDestroy _h;
                missionNamespace setVariable [_x, -1];
                private _logMsg = format ["NVG exit: destroyed %1 (was %2)", _x, _h];
                AEE_LOG_DEBUG(_logMsg);
            };
        } forEach [
            QGVAR(ppHandle_NVG_CC),
            QGVAR(ppHandle_NVG_Bloom),
            QGVAR(ppHandle_NVG_Vignette),
            QGVAR(ppHandle_NVG_Grain),
            QGVAR(ppHandle_NVG_DoF)
        ];
        AEE_LOG_INFO("NVG effects torn down (vision mode left)");

        // Tear down the tube-face overlay the moment NVG is removed.
        QGVAR(nvgDisplay) cutText ["", "PLAIN"];
        missionNamespace setVariable [QGVAR(nvgDisplayUp), false];

        missionNamespace setVariable [QGVAR(nvgGrainActive), false];
    };
    // Clear stale tube state so diagnostics and scripts do not read
    // values from a previous NVG session.
    missionNamespace setVariable [QGVAR(nvgTubeTier), "NONE"];
    missionNamespace setVariable [QGVAR(nvgGain), 0];
    missionNamespace setVariable [QGVAR(nvgNoise), 0];
    missionNamespace setVariable [QGVAR(nvgBlowout), 0];
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
// phosphorTint = [R, G, B, A] colour of the phosphor screen.  This is the
//   ColorCorrections colorize array.  The engine's own NVG is already a
//   dim green; the colorize AMPLIFIES it (values above 1.0) rather than
//   replacing it.  Killing a channel (0.0) darkens the image into black.
//   P43 (green): peak 545nm (ACE3 green preset shape [1.3, 1.2, 0, 0.9]).
//   P45 (white): ~545nm broadband (ACE3 white preset shape [1.1, 0.8, 1.9, 0.9]).
//   P20 (yellow-green): older phosphor, peak ~550nm, warmer than P43.
// nvgWeight = [R, G, B, 0] colour weights for desaturation (ColorCorrections
//   param 6, default [0.299, 0.587, 0.114, 0]).  ACE3 uses [6, 1, 1, 0] for
//   green phosphor and [1, 1, 6, 0] for white.  Do NOT use [0, 0, 0, 0] —
//   a zero desaturation weighting breaks the effect.
// chromaStrength = ChromAberration per-channel sample spacing (BIS wiki).
//   Wiki default 0.005; >= ~0.02 causes visible "drunk doubling".
//   NVG objectives are achromatic multi-element designs corrected for
//   600-900nm.  Tiers sit at 0.002-0.008 (subtle edge fringing only).
// Sensitivity = photocathode luminous sensitivity in µA/lm (datasheet
// values, Wikipedia "Image intensifier": Gen 1 S-25 ~250, Gen 2 ~550,
// Gen 3 GaAs ~1100, filmless 4G/PVS-31 ~2000).  The RATIOS are physics.
// The absolute scale is converted to a detected-photon count by
// PHOTON_SCALE — a single calibration constant (cathode area × quantum
// efficiency × integration time ÷ electron charge), NOT per-tier magic
// numbers.  Tuning is one knob, not four.
#define AEE_PHOTON_SCALE 500
private _sensitivity = 550;
private _noiseFloor = 0.15;
private _mtf15 = 0.45;
private _phosphorTint = [1.3, 1.2, 0.0, 0.9];
private _nvgWeight = [6, 1, 1, 0];
private _chromaStrength = 0.006;
private _vigStrength = [0.0040, 0.0040, 0.06, 0.06];
private _bloomBase = 0.04;
private _bloomScale = 0.04;

// Tier matcher by HMD classname.  Substring tests run most-specific first.
// The ENVG-II (NVGogglesB_grn_F/blk_F/gry_F, Apex) and panoramic GPNVG-class
// goggles are modern FILMLESS devices — Gen 4 equivalent, same tube class as
// the PVS-31A (L3Harris sell sheet / ACE3 generation=4 mapping).  They get
// the filmless constants, not plain GEN3.
if (_hmd find "USP_PVS31" >= 0 || _hmd find "PVS31" >= 0 || _hmd find "USP_PVS_31" >= 0
    || _hmd find "NVGogglesB" >= 0 || _hmd find "GPNVG" >= 0 || _hmd find "NVG_Wide" >= 0) then {
    _tier = "PVS31";
    _sensitivity = 2000;     // filmless GaAs (L3Harris/Photonis 4G)
    _noiseFloor = 0.03;
    _mtf15 = 0.65;
    _phosphorTint = [1.1, 0.8, 1.9, 0.9];
    _nvgWeight = [1, 1, 6, 0];
    _chromaStrength = 0.002;
    _vigStrength = [0.0025, 0.0025, 0.06, 0.06];
    _bloomBase = 0.02;
    _bloomScale = 0.02;
} else {
    if (_hmd find "NVGen3" >= 0 || _hmd find "NVGoggles_INDEP" >= 0) then {
        _tier = "GEN3";
        _sensitivity = 1100;     // GaAs (Photonis, ~700-1200 µA/lm)
        _noiseFloor = 0.04;
        _mtf15 = 0.61;
        _phosphorTint = [1.3, 1.2, 0.0, 0.9];
        _nvgWeight = [6, 1, 1, 0];
_chromaStrength = 0.004;
    _vigStrength = [0.0030, 0.0030, 0.06, 0.06];
    _bloomBase = 0.03;
    _bloomScale = 0.03;
    } else {
        if (_hmd find "NVGen2" >= 0 || _hmd find "NVGoggles_OPFOR" >= 0) then {
            _tier = "GEN2";
            _sensitivity = 550;      // multialkali Gen 2
            _noiseFloor = 0.08;
            _mtf15 = 0.45;
            _phosphorTint = [1.3, 1.2, 0.0, 0.9];
            _nvgWeight = [6, 1, 1, 0];
_chromaStrength = 0.006;
    _vigStrength = [0.0040, 0.0040, 0.06, 0.06];
    _bloomBase = 0.04;
    _bloomScale = 0.04;
        } else {
            if (_hmd find "GEN1" >= 0 || _hmd find "NVGoggles" >= 0) then {
                _tier = "GEN1";
                _sensitivity = 250;      // S-25 multialkali
                _noiseFloor = 0.15;
                _mtf15 = 0.30;
                _phosphorTint = [1.4, 1.3, 0.0, 0.9];
                _nvgWeight = [6, 1, 1, 0];
                _chromaStrength = 0.008;
                _vigStrength = [0.0050, 0.0050, 0.06, 0.06];
                _bloomBase = 0.05;
                _bloomScale = 0.05;
            };
        };
    };
};
missionNamespace setVariable [QGVAR(nvgTubeTier), _tier];

// Log tier detection once per NVG session (INFO, not per-tick): the hmd
// classname and resolved tier tell us immediately whether the device was
// recognised.  "AUTO" means the classname matched nothing — the effects
// still run but with the default (GEN2-ish) constants.
private _tierLogKey = format ["%1_%2", _hmd, _tier];
if (missionNamespace getVariable [QGVAR(nvgTierLogged), ""] != _tierLogKey) then {
    missionNamespace setVariable [QGVAR(nvgTierLogged), _tierLogKey];
    private _logMsg = format ["NVG tier: hmd=%1 -> %2", _hmd, _tier];
    AEE_LOG_INFO(_logMsg);
};

// ─── Temperature coupling ─────────────────────────────────────────────────
// Tube performance degrades with temperature.  Photocathode quantum
// efficiency and MCP gain both fall in cold; dark current rises in heat
// (raising noise).  Military spec (MIL-PRF-49428F): operating range
// -51 to +49 °C with reduced performance at the extremes.
//
// Sensitivity scales 1.0 at 20 °C, ~0.7 at -30 °C, ~0.9 at 45 °C.
// The noise floor rises with temperature (more thermal emission, more
// MCP noise): +60% from 20 °C to 45 °C.
private _airTemp = missionNamespace getVariable [QEGVAR(core,currentTemperature), 20];
if !(_airTemp isEqualType 0) then { _airTemp = 20; };
// Gain peaks at ~20 °C, falls in cold (cathode/MCP gain drop) and in
// heat (thermal emission saturates MCP).  Piecewise: 0.7 @ -30, 1.0 @ 20,
// 0.85 @ 45.
private _tempGainFactor = if (_airTemp < 20) then {
    linearConversion [-30, 20, _airTemp, 0.7, 1.0, true]
} else {
    linearConversion [20, 45, _airTemp, 1.0, 0.85, true]
};
_sensitivity = _sensitivity * _tempGainFactor;
// Dark current (hence noise floor) rises with temperature: +60% from
// 20 °C to 45 °C.
private _noiseTempFactor = linearConversion [20, 45, _airTemp, 1.0, 1.6, true];
_noiseFloor = _noiseFloor * _noiseTempFactor;

// ─── Ambient light in lux ────────────────────────────────────────────────
// From the shared illuminance layer (fnc_calculateIlluminance): the
// validated moonIntensity/overcast/rain lux model, plus client dynamic
// lux from getLightingAt.  One lux value feeds NVG, thermal, glare and
// ballistics instead of each module estimating independently.
private _lux = missionNamespace getVariable [QGVAR(illuminanceLux), 0.001];
if !(_lux isEqualType 0) then { _lux = 0.001; };
_lux = _lux max 0.001;

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
//
// AGC lag: a real AGC has a time constant (~100 ms) — gain does not jump
// instantly when the light level changes.  The stored gain approaches the
// target exponentially with a smoothing factor per 0.1 s tick.  Sweeping
// the tube across a bright source produces a visible gain "settle".
private _gainTarget = _sensitivity / (_lux + 1);
_gainTarget = _gainTarget min _sensitivity;
private _gain = missionNamespace getVariable [QGVAR(nvgGain), _gainTarget];
if (_gain isEqualType 0) then {
    _gain = _gain + (_gainTarget - _gain) * 0.5;
} else {
    _gain = _gainTarget;
};
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
private _photonCount = _lux * _sensitivity * AEE_PHOTON_SCALE;
private _shotNoise = 1 / sqrt(_photonCount + 1);
private _noise = _noiseFloor + (1 - _noiseFloor) * _shotNoise;
_noise = 0.03 max _noise min 1;
missionNamespace setVariable [QGVAR(nvgNoise), _noise];

// ─── Bright-source detection (auto-gating / blooming) ────────────────────
// Real tubes respond to a bright source entering the view (US4952793A,
// Cold Harbour NV terminology): the MCP gate closes in <15 ns-100 µs,
// or the phosphor blooms white for un-gated tubes.  Detect static bright
// emitters (street lamps, fires, flares) in the view cone; muzzle flash
// is handled by the fired event (ACE3 pattern).
//
// Intensity = angular proximity (dead-centre = 1.0, edge of FOV = 0)
//            × distance falloff (150 m range).
// The value decays exponentially: instant rise (gate/bloom engage fast),
// tier-dependent recovery (Gen 1 blooms linger for seconds, gated Gen 3
// recovers in ~100 ms).
private _eye = eyePos _player;
private _viewDir = vectorDirVisual _player;
// Dynamic bright-source detection — NO hardcoded classnames.  Any object
// whose simulation is a light emitter qualifies, so vanilla and every mod
// (lamp packs, IR strobes, vehicle lights) works without a compat list.
//   - simulation == "Lamps"     : street lamps (vanilla + mods that inherit)
//   - simulation == "nvmarker"  : IR strobes (vanilla + ACE3)
//   - isLightOn _x              : any vehicle with headlights on
//   - isKindOf "F_40_White"     : flare projectiles (bright transients)
// The config lookup uses configOf (the object's own config) so it works
// for ANY class — vanilla or modded.  (sqflint cannot parse configOf and
// reports a false positive; HEMTT's linter requires configOf over typeOf.)
private _brightSources = nearestObjects [_eye, [], 150];
private _blowoutNow = 0;
{
    private _sim = getText ((configOf _x) >> "simulation");
    private _isBright = false;
    if (_sim == "Lamps" || _sim == "nvmarker") then { _isBright = true; };
    if (isLightOn _x) then { _isBright = true; };
    if (_x isKindOf "F_40_White") then { _isBright = true; };
    if (_isBright) then {
        private _dirTo = _eye vectorFromTo (getPosASL _x);
        private _ang = acos ((_viewDir vectorDotProduct _dirTo) max -1 min 1);
        // Gate triggers when the source enters the tube's FOV.  AN/AVS-9
        // FOV is 40° circular (DTIC ADA426388, NASA 20030063076, Elbit
        // datasheet) — half-angle 20°.
        if (_ang < 20) then {
            private _dist = _eye distance (getPosASL _x);
            // Illuminance at the photocathode follows the inverse square
            // law: E = I/d².  Gate intensity scales with the light that
            // actually reaches the tube.  Normalised so a dead-centre
            // source at 10 m is ~1.0; at 150 m it is ~0.004 (negligible).
            private _intensity = (1 - _ang / 20) * (100 / (_dist * _dist));
            _blowoutNow = _blowoutNow max _intensity;
        };
    };
} forEach _brightSources;

// Muzzle flash / explosive flash: the fired event stamps nvgFlashUntil.
if (CBA_missionTime < (missionNamespace getVariable [QGVAR(nvgFlashUntil), -1])) then {
    _blowoutNow = _blowoutNow max 0.9;
};

// Exponential envelope: instant attack, slow tier-dependent release.
// Gen 1 (no gating) blooms for seconds; Gen 3/PVS-31 gate recovers fast.
private _release = switch (_tier) do {
    case "GEN1": { 0.25 };   // ~4 s to fade
    case "GEN2": { 0.45 };
    default { 0.85 };        // gated: ~0.6 s
};
private _blowout = missionNamespace getVariable [QGVAR(nvgBlowout), 0];
if (_blowout isEqualType 0) then {
    _blowout = (_blowout * (1 - _release)) max _blowoutNow;
    _blowout = _blowout max (_blowoutNow);
} else {
    _blowout = _blowoutNow;
};
missionNamespace setVariable [QGVAR(nvgBlowout), _blowout];

// ─── MTF degradation at low light ─────────────────────────────────────────
// Resolution (hence perceived contrast) drops as photon flux falls —
// fewer detected photons = poorer signal, and the AGC at max gain cannot
// restore the missing modulation.  The tier's published MTF (mtf15) is
// only reached at good light; at starlight the effective contrast fades
// toward 55 % of the tier value.  The contrast floor keeps the image
// watchable — the sensor still has some signal even in darkness.
//
// Bright Spot Protection (Cold Harbour): while a bright source is gating
// the tube, photocathode voltage is reduced to protect it, which LOWERS
// RESOLUTION.  Gated tubes (Gen 3, PVS-31) lose up to 40 % contrast while
// gating; un-gated Gen 1/2 keep full MTF (they bloom instead).
// Input range is [0, 1] noise: 0 (full moon, low noise) = full MTF,
// 1 (starlight, high noise) = degraded toward 55 %.
private _mtfEffective = linearConversion [0, 1, _noise, _mtf15, _mtf15 * 0.55, true];
if (_blowout > 0 && (_tier == "GEN3" || _tier == "PVS31")) then {
    _mtfEffective = _mtfEffective * (1 - _blowout * 0.4);
};

// ─── Bloom (bright-source halos scale with ambient light) ────────────────
// Halo diameter is a fixed physical property of the tube (0.7-1.0mm for
// Gen 3, measured on the 18mm tube face).  The DynamicBlur effect
// simulates the visual impact of these halos, which scale with scene
// brightness.  At starlight, halos are less visible (dark scene).  At
// full moon, brighter sources produce more noticeable blooming.
// Values stay within ACE3's proven 0.05-0.11 band (ST_NVG_BLUR_MIN/MAX);
// blur above ~0.1 smears the image.
private _bloom = _bloomBase + _bloomScale * (_moonLight / 1.0);
_bloom = 0 max _bloom min 1;

// ─── Brightness (AGC output, physics-driven) ──────────────────────────────
// The AGC model above (gain = sensitivity/(lux+1)) describes the tube's
// light amplification.  Brightness is the AGC output normalised against
// the documented scale anchors: 1.0 = unchanged (BIS wiki), 0.65 = the
// lowest the engine renders visibly (ACE3-proven floor).
//
// Full moon (lux ~0.25) drives the tube to its MOB clamp: brightness
// approaches 1.0 (faithful reproduction of the engine's already-amplified
// NVG).  Starlight (lux ~0.001) starves the tube: gain is maxed but few
// photons arrive, so the image dims toward the visible floor.  The value
// rides the same _lux the gain and shot-noise models use — environment
// drives the output, not a fixed preset.
private _brightness = linearConversion [0.001, 0.25, _lux, 0.65, 1.0, true];

// ─── Bright-source response (bloom vs gate) ───────────────────────────────
// Un-gated Gen 1/2 tubes BLOOM: the phosphor saturates and the whole image
// whites out (brightness climbs toward 2.0 = white).  Recovery is slow
// because the phosphor and AGC must settle.
//
// Gated Gen 3 / PVS-31 tubes GATE: the MCP cuts gain to protect the
// photocathode, so the image goes DARK (brightness collapses) for as long
// as the source is in view.  This is the "flashbang" effect — a bright
// light blinds a gated tube by blacking it out, not whiting it out.
if (_blowout > 0) then {
    if (_tier == "GEN1" || _tier == "GEN2") then {
        _brightness = _brightness + _blowout * (1 - _brightness);
    } else {
        _brightness = _brightness * (1 - _blowout * 0.85);
    };
};

// ─── FilmGrain parameters (shot noise) ───────────────────────────────────
// Grain sharpness and size scale with noise level.  At high noise
// (starlight), grain is coarse and sharp.  At low noise (full moon),
// grain is fine and soft.  Ranges follow ACE3 (ST_NVG_NOISESHARPNESS_*
// 1.0-1.2, ST_NVG_GRAIN_* 2.25-2.7).  Monochromatic = 0 (grayscale grain:
// BIS wiki states 0 = monochrome, any other value = colour).  Grayscale
// suits both P45 white and P43 green phosphor (tube scintillation is
// monochrome).
private _sharpness = linearConversion [1, 0, _noise, 1.2, 1.0, true];
private _grainSize = linearConversion [1, 0, _noise, 2.7, 2.25, true];

// ─── Recreate all NVG handles every tick ─────────────────────────────────
// ACE3 pattern: recreate ppEffect handles so effects survive alt-tab,
// resize, AT sights, etc.  Recreation happens ONLY when a handle is
// missing (the engine killed it) — never on a timer, which would destroy
// and rebuild live effects and cause visible flicker every cycle.
//
// Priorities follow the BIS wiki base order — lower applies first, higher
// applies last (on top): RadialBlur 100 < ChromAberration 200 <
// DynamicBlur 400 < ColorCorrections 1500 < FilmGrain 2000.  Values are
// offset into a free band so they never collide with the persistent
// normal-vision handles (2000/3000/4000/5000) or thermal (1300/4200/5200).
// ppEffectCreate returns -1 when a priority is taken (BIS wiki), so each
// create bumps until it succeeds.
//
// ChromAberration is shared with fnc_managePostProcess (priority 3000):
// reuse its handle instead of creating a second effect at that priority.
private _hChroma = missionNamespace getVariable [QGVAR(ppHandle_ChromAberration), -1];
private _hCC     = missionNamespace getVariable [QGVAR(ppHandle_NVG_CC), -1];
private _hBloom  = missionNamespace getVariable [QGVAR(ppHandle_NVG_Bloom), -1];
private _hVig    = missionNamespace getVariable [QGVAR(ppHandle_NVG_Vignette), -1];
private _hGrain  = missionNamespace getVariable [QGVAR(ppHandle_NVG_Grain), -1];

// DepthOfField is ENHANCEMENT-ONLY: if the engine refuses to create it
// (returns -1 — this can happen if the effect is unavailable on this
// build), it must NOT trigger recreation of the essential handles.  A
// permanent -1 DoF handle in the _missing check would destroy and
// recreate CC/bloom/vignette/grain every 0.1 s tick, leaving the image
// vanilla and flooding the RPT with "Invalid post effect handle".
// DoF gets its own create-if-missing block further down.
private _missing = (_hCC < 0 || _hBloom < 0 || _hVig < 0 || _hGrain < 0);

if (_missing) then {
    // Destroy any live handles first so the bump loop can reclaim the
    // base priorities instead of climbing past them and leaking effects.
    {
        private _h = missionNamespace getVariable [_x, -1];
        if (_h >= 0) then {
            ppEffectDestroy _h;
            missionNamespace setVariable [_x, -1];
            private _logMsg = format ["destroyed NVG handle %1 (was %2)", _x, _h];
            AEE_LOG_DEBUG(_logMsg);
        };
    } forEach [
        QGVAR(ppHandle_NVG_CC),
        QGVAR(ppHandle_NVG_Bloom),
        QGVAR(ppHandle_NVG_Vignette),
        QGVAR(ppHandle_NVG_Grain)
    ];

    if (_hChroma < 0) then {
        private _prio = 3000;
        private _guard = 0;
        while {_hChroma < 0 && _guard < 100} do {
            _hChroma = ppEffectCreate ["ChromAberration", _prio];
            _prio = _prio + 1;
            _guard = _guard + 1;
        };
        missionNamespace setVariable [QGVAR(ppHandle_ChromAberration), _hChroma];
        private _logMsg = format ["recreated NVG ChromAberration handle=%1", _hChroma];
        AEE_LOG_DEBUG(_logMsg);
    };

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
        private _logMsg = format ["created NVG %1 priority=%2 handle=%3", _name, _priority, _handle];
        AEE_LOG_DEBUG(_logMsg);
    } forEach [
        ["RadialBlur",       1200, QGVAR(ppHandle_NVG_Vignette)],
        ["DynamicBlur",      4100, QGVAR(ppHandle_NVG_Bloom)],
        ["ColorCorrections", 5100, QGVAR(ppHandle_NVG_CC)],
        ["FilmGrain",        6000, QGVAR(ppHandle_NVG_Grain)]
    ];
    _handles params ["_hVig", "_hBloom", "_hCC", "_hGrain"];
};

// ─── Depth of field (objective focus) — enhancement only ──────────────────
// Created in its OWN block so a failure here cannot disturb the essential
// NVG handles above.  If DepthOfField is unavailable on this build the
// handle stays -1 and the feature is silently skipped (one WARN line).
private _hDoF = missionNamespace getVariable [QGVAR(ppHandle_NVG_DoF), -1];
if (_hDoF < 0) then {
    private _dofPrio = 868;   // TFN NVG Effects proven priority
    _hDoF = ppEffectCreate ["DepthOfField", _dofPrio];
    private _guard = 0;
    while {_hDoF < 0 && _guard < 100} do {
        _dofPrio = _dofPrio + 1;
        _hDoF = ppEffectCreate ["DepthOfField", _dofPrio];
        _guard = _guard + 1;
    };
    missionNamespace setVariable [QGVAR(ppHandle_NVG_DoF), _hDoF];
    if (_hDoF >= 0) then {
        private _logMsg = format ["created NVG DepthOfField priority=%1 handle=%2", _dofPrio, _hDoF];
        AEE_LOG_INFO(_logMsg);
    } else {
        AEE_LOG_WARN("DepthOfField unavailable on this build - NVG DoF disabled");
    };
};

// ─── Depth of field (objective focus) ─────────────────────────────────────
// A real NVG objective lens has a focus distance: objects at that range are
// sharp, nearer and farther blur.  The user sets it with the objective focus
// ring; we model the same by focusing on what the player is looking at.
//
// Technique verified from workshop mod TFN NVG Effects (workshop 3682613859):
// DepthOfField is a real, scriptable player-view effect — the BIS wiki marks
// it "TBD" but production mods use it with ppEffectForceInNVG true and
// ppEffectAdjust [blur, distance, 1].  Our previous "not scriptable" note
// was wrong (camSetFocus is camera-only, but DepthOfField ppEffect works).
//
// Focus distance: distance to the cursor target, clamped to a sane range.
// The blur magnitude scales with how far the object is from the focus plane
// — larger blur = shallower depth of field (worse optics).  Tiers get
// different blur strengths: Gen 1/2 objective blur more than Gen 3/4.
private _focusDist = 50;
private _focusTarget = cursorTarget;
if (!isNull _focusTarget) then {
    _focusDist = (_player distance _focusTarget) max 5 min 500;
};
private _dofBlur = switch (_tier) do {
    case "PVS31": { 1.5 };
    case "GEN3":  { 2.5 };
    case "GEN2":  { 4.0 };
    default      { 5.0 };   // Gen 1: shallow, hard-to-focus objective
};
if (_hDoF >= 0) then {
    _hDoF ppEffectAdjust [_dofBlur, _focusDist, 1];
    _hDoF ppEffectForceInNVG true;
    _hDoF ppEffectCommit 0;
};

// Diagnostics: set aee_optics_nvgDebug = true in the debug console to log
// every tick's handles and params to the .rpt.  ppEffectCreate returns -1
// when the priority is taken — a -1 handle means the effect did not apply.
// gain and lux are the AGC inputs: gain must fall as lux rises (the
// inverse-lux auto-gating response) — the two numbers prove the gate works.
if (missionNamespace getVariable [QGVAR(nvgDebug), false]) then {
    diag_log text format [
        "[AEE] NVG tick | tier=%1 moon=%2 lux=%3 gain=%4 visMode=%5 hmd=%6 | handles CC=%7 chroma=%8 bloom=%9 vig=%10 grain=%11 dof=%12 | CC params %13 | bloom=%14 grain=%15 | blowout=%16 | dofBlur=%17 focusDist=%18",
        _tier,
        _moonLight,
        _lux,
        _gain,
        currentVisionMode _player,
        _hmd,
        _hCC,
        _hChroma,
        _hBloom,
        _hVig,
        _hGrain,
        _hDoF,
        [_brightness, _mtfEffective, 0, [0,0,0,0], _phosphorTint, _nvgWeight],
        _bloom,
        [_noise, _sharpness, _grainSize, 0.5, 1.0, 0],
        _blowout,
        _dofBlur,
        _focusDist
    ];
};

// ─── ChromAberration (optical imperfection) ──────────────────────────────
// Lateral colour from residual dispersion in the objective lens.
// NVG objectives are achromatic multi-element designs corrected for
// 600-900nm (BK7 crown Vd=64.2, SF2 flint Vd=33.8).
// _chromaStrength is the per-channel sample spacing (BIS wiki).  The
// default is 0.005; values >= ~0.02 visibly split R/G/B into a "drunk
// doubling".  Tiers stay at 0.002-0.008: subtle edge fringing only.
_hChroma ppEffectAdjust [_chromaStrength, _chromaStrength, false];
_hChroma ppEffectEnable true;
_hChroma ppEffectForceInNVG true;
_hChroma ppEffectCommit 0;

// ─── ColorCorrections (phosphor tint + brightness + contrast) ───────────
// Params: [brightness, contrast, offset, blend, colorize, weight]
//
// brightness: ACE3-proven 0.65..0.75 band (see above).
// contrast: MTF at 15 lp/mm.  GEN3 P43: 61% (Elbit MX-10160).
//   PVS-31A: ~65% (estimated from 64-81 lp/mm resolution).
//   GEN2: ~45% (estimated from 47-54 lp/mm).
//   GEN1: ~30% (estimated from 30-40 lp/mm).
// colorize: phosphor screen tint, AMPLIFIED above 1.0 against the
//   engine's already-green NVG image.  P43 peak 545nm (green):
//   [1.3, 1.2, 0.0, 0.9] = ACE3 green preset.  P45 broadband ~545nm
//   (white): [1.1, 0.8, 1.9, 0.9] = ACE3 white preset.
//   P20 peak ~550nm (yellow-green): warmer green.
// weight: desaturation RGB weights, non-zero.  [6, 1, 1, 0] = ACE3 green,
//   [1, 1, 6, 0] = ACE3 white.  [0,0,0,0] disables the effect.
_hCC ppEffectAdjust [_brightness, _mtfEffective, 0, [0,0,0,0], _phosphorTint, _nvgWeight];
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
// _vigStrength = [powerX, powerY, offsetX, offsetY] (ACE3 magnitudes:
//   power ~0.0025-0.005, offset ~0.06 = 6% of screen un-blurred).
//   Do NOT scale power above ~0.01: RadialBlur power 0.5 with a small
//   offset smears the whole image into black.
_hVig ppEffectAdjust _vigStrength;
_hVig ppEffectEnable true;
_hVig ppEffectForceInNVG true;
_hVig ppEffectCommit 0;

// ─── FilmGrain (shot noise - the NVG aesthetic) ──────────────────────────
_hGrain ppEffectAdjust [_noise, _sharpness, _grainSize, 0.5, 1.0, 0];
_hGrain ppEffectEnable true;
_hGrain ppEffectForceInNVG true;
_hGrain ppEffectCommit 0;

// ─── Tube face display (mask + fiber-optic bundle) ───────────────────────
// Show the circular tube overlay.  The mask's transparent centre lets the
// NVG image through; opaque black outside forms the round goggle image.
//
// The fiber "chicken wire" is fixed-pattern noise, not a texture: the
// multi-fiber bundle boundaries (0.5-1 mm on an 18 mm tube = 3-5 % of
// diameter) are a low-contrast artifact (SCHOTT datasheets, Hamamatsu
// on Gen 3 "eliminating" it).  Alpha is therefore crushed to noise levels
// and scales with _noise — relatively more visible at high gain against
// flat dark, washed out at full moon where shot noise dominates.
//
// cutRsc on an already-open layer restarts the display (flicker), so it
// is called once per entry; the fiber texture + fade update every tick.
private _fiberBase = switch (_tier) do {
    case "GEN1": { 0.10 };
    case "GEN2": { 0.05 };
    default { 0.0 };
};
private _fiberAlpha = _fiberBase * linearConversion [0.03, 1, _noise, 0.35, 1.0, true];
private _fiberTex = switch (_tier) do {
    case "GEN1": { QPATHTOF(data\nvg_fibers_gen1_1024.paa) };
    case "GEN2": { QPATHTOF(data\nvg_fibers_gen2_1024.paa) };
    default { "" };
};
if !(missionNamespace getVariable [QGVAR(nvgDisplayUp), false]) then {
    QGVAR(nvgDisplay) cutRsc [QGVAR(nvgTitle), "PLAIN", 0, false, false];
    missionNamespace setVariable [QGVAR(nvgDisplayUp), true];
};
private _disp = uiNamespace getVariable [QGVAR(titleDisplay), displayNull];
if (!isNull _disp) then {
    private _fibers = _disp displayCtrl 1001;
    _fibers ctrlSetFade (1 - _fiberAlpha);
    _fibers ctrlSetText _fiberTex;
    _fibers ctrlCommit 0;
};

// ─── Eye accommodation (exposure) ───────────────────────────────────────
// setAperture is the camera's eye-accommodation aperture — LIGHT INTAKE,
// not depth of field (BIS wiki: "Sets custom eye accommodation camera
// aperture"; Namikaze calibration: 50 = daylight outdoor, 30 = daylight
// indoor, <20 = very bright scene suitable for night).
//
// The phosphor screen output is AGC-clamped to a constant MOB regardless
// of scene brightness (Elbit MX-10160: 2.8-4.2 fL held across 1-20 fc),
// so the eye looking at the tube sees a constant-brightness display.  The
// exposure is therefore a FIXED night value, not dynamic.  A3TI proves 15
// works in-game (workshop 2041057379).  -1 restores the engine default.
//
// True depth of field (distance-based blur) is camSetFocus — camera-only
// (camCreate), not available on the player view.  The engine's player-view
// DoF is not scriptable; the RadialBlur edge softening approximates the
// objective's focus behaviour instead.
setAperture 15;
missionNamespace setVariable [QGVAR(nvgGrainActive), true];
