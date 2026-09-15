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
        (["aee_optics_nvg_title"] call BIS_fnc_rscLayer) cutText ["", "PLAIN"];
        missionNamespace setVariable [QGVAR(nvgDisplayUp), false];

        missionNamespace setVariable [QGVAR(nvgGrainActive), false];
    };
    // Clear stale tube state so diagnostics and scripts do not read
    // values from a previous NVG session.
    missionNamespace setVariable [QGVAR(nvgTubeTier), "NONE"];
    missionNamespace setVariable [QGVAR(nvgGain), 0];
    missionNamespace setVariable [QGVAR(nvgNoise), 0];
    missionNamespace setVariable [QGVAR(nvgBlowout), 0];
    missionNamespace setVariable [QGVAR(nvgBlowoutHold), 0];
    missionNamespace setVariable [QGVAR(nvgWetness), 0];
    missionNamespace setVariable [QGVAR(nvgBattery), 1.0];
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
private _vigStrength = [0.0040, 0.0040, 0.06, 0.06];
private _bloomBase = 0.04;
private _bloomScale = 0.04;

// ─── Per-device objective-focus config (researched, not guessed) ─────────
// Real NVGs are MANUAL-focus: the operator sets the objective once and the
// image is sharp from the near limit to infinity (hyperfocal behaviour),
// not a camera-style racking band.  Only the ENVG family has real
// autofocus.  Sources: DHS TechNote, L3Harris/Elbit sell sheets, operator
// manuals (near limits: PVS-14/7 0.25 m, PVS-31A & GPNVG 0.45 m).
//   dofModeDefault: 0 = AUTO (state machine), 1 = MANUAL (ring)
//   dofNearLimit:   objective near focus limit, metres
//   dofDefaultDist: where the ring sits when the player first puts the
//                   goggles on - hyperfocal (~12-24 m at f/1.2 27 mm,
//                   CoC 25-50 um), 15 m mid-range.  Not 300 m.
private _dofModeDefault = 1;    // manual by default: real NVGs are manual
private _dofNearLimit = 0.25;
private _dofDefaultDist = 15;   // hyperfocal mid-band
private _dofMaxDist = 300;
// Tube count used for vignette geometry (lens rim radius).
// Real devices: PVS-14 monocular (1), PVS-31A/DTNVS binocular (2),
// GPNVG-18 panoramic quad (4).
private _tubeCount = 1;

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
    _vigStrength = [0.0025, 0.0025, 0.06, 0.06];
    _bloomBase = 0.02;
    _bloomScale = 0.02;
    // Objective focus: PVS-31A/GPNVG manual with 0.45 m near limit;
    // the ENVG-II fusion goggle (NVGogglesB_grn_F) is the autofocus
    // member of the family (L3Harris ENVG autofocus objective).
    _dofModeDefault = parseNumber ((_hmd find "NVGogglesB_grn_F") < 0);
    _dofNearLimit = 0.45;
    _dofDefaultDist = 20;   // PVS-31A/GPNVG ring, hyperfocal for f/1.4
    _tubeCount = [4, 2] select ((_hmd find "GPNVG" >= 0 || _hmd find "NVG_Wide" >= 0) isEqualTo false);
} else {
    if (_hmd find "NVGen3" >= 0 || _hmd find "NVGoggles_INDEP" >= 0) then {
        _tier = "GEN3";
        _sensitivity = 1100;     // GaAs (Photonis, ~700-1200 µA/lm)
        _noiseFloor = 0.04;
        _mtf15 = 0.61;
        _phosphorTint = [1.3, 1.2, 0.0, 0.9];
        _nvgWeight = [6, 1, 1, 0];
    _vigStrength = [0.0030, 0.0030, 0.06, 0.06];
    _bloomBase = 0.03;
    _bloomScale = 0.03;
        _dofModeDefault = 1;     // PVS-14-style manual, 0.25 m near limit
        _dofNearLimit = 0.25;
        _dofDefaultDist = 15;
    } else {
        if (_hmd find "NVGen2" >= 0 || _hmd find "NVGoggles_OPFOR" >= 0) then {
            _tier = "GEN2";
            _sensitivity = 550;      // multialkali Gen 2
            _noiseFloor = 0.08;
            _mtf15 = 0.45;
            _phosphorTint = [1.3, 1.2, 0.0, 0.9];
            _nvgWeight = [6, 1, 1, 0];
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
                _vigStrength = [0.0050, 0.0050, 0.06, 0.06];
                _bloomBase = 0.05;
                _bloomScale = 0.05;
            };
        };
    };
};
missionNamespace setVariable [QGVAR(nvgTubeTier), _tier];

// ─── Tube-edge vignette (lens rim) — PHYSICS-derived, not ACE3's tuning ──
// RadialBlur offset = "relative size of un-blurred centre" in screen
// units.  The lens-edge falloff must put the un-blurred centre AT the
// tube rim, so the blur starts exactly where the glass meets the
// housing.  The engine's NVG circle radius is a fraction of safeZoneH.
// Convert to screen units:
//   offsetY = radius_frac * (square_H / screen_H)  = radius_frac (16:9)
//   offsetX = radius_frac * (square_W / screen_W)  = radius_frac / aspect
// ACE3's bluRadius (0.15/0.26) is their tuning for their mask geometry,
// not a physics value - the proof-of-concept, not the source.  These are
// derived from the engine's NVG circle radius so the blur sits on the
// lens rim.
private _tubeRadius = switch (_tubeCount) do {
    case 2:  { 0.40 };
    case 4:  { 0.24 };
    default { 0.44 };
};
private _vigAspect = getResolution select 4;
if (_vigAspect <= 0) then { _vigAspect = 16.0 / 9.0; };
private _vigOffY = _tubeRadius;
private _vigOffX = _tubeRadius / _vigAspect;
_vigStrength set [2, _vigOffX];
_vigStrength set [3, _vigOffY];

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

// ─── Rain: Mie scattering noise penalty ──────────────────────────────────
// Forward-scattered light from rain adds photon noise across the entire
// image (Mie scattering volume).  The MCP amplifies this scattered light
// equally with the signal, degrading SNR.  Heavy rain can drop SNR
// 60-80% (research: SNR reduction ∝ rain_intensity × drop_density ×
// forward_scatter_coefficient).  Model as an additive noise floor increase.
if (rain > 0.2) then {
    private _mieNoise = rain * 0.35;   // heavy rain: +35% noise floor
    _noise = (_noise + _mieNoise) min 1;
};

_noise = 0.03 max _noise min 1;
missionNamespace setVariable [QGVAR(nvgNoise), _noise];

// ─── Battery-level degradation ───────────────────────────────────────────
// Real NVGs are powered by a single BA-5567/U battery (1.5 V lithium,
// ~4 Wh).  As voltage drops, the MCP bias falls, reducing gain and
// increasing noise.  Image quality degrades progressively.
//
// Model: nvgBattery tracks 0.0 (dead) to 1.0 (fresh).  Drain rate
// depends on gain (high gain = more MCP current = faster drain) and
// temperature (extreme cold reduces battery capacity; extreme heat
// increases self-discharge).  At 0.3 and below, noise floor rises;
// at 0.15, scan-line flicker appears; at 0.05, intermittent dropout.
// Battery persists per session (missionNamespace) and resets on NVG exit.
private _battery = missionNamespace getVariable [QGVAR(nvgBattery), 1.0];
if !(_battery isEqualType 0) then { _battery = 1.0; };

// Drain rate: per-tier base matched to real-world battery life on a single
// AA lithium cell at 25 °C, typical nighttime use (gain ≈ sensitivity).
//
//   PVS31  16 hrs avg  L3Harris PVS-31A datasheet
//   GEN3   65 hrs avg  TM 11-5855-306-10 Table 2-3 (lithium L91, negligible IR)
//   GEN2   35 hrs est  multialkali Gen 2, single tube, 1× AA
//   GEN1   25 hrs est  S-25 multialkali, single tube, 1× AA
//
// gainRatio = gain / sensitivity (1.0 at full darkness, <1.0 in moderate light).
// Temperature derating is read from the physiology module (Issue #36); see
// the batteryTemperatureDerating read below.
private _baseDrain = switch (_tier) do {
    case "PVS31": { 0.0000174 };  // 1 / (16 × 3600)
    case "GEN3":  { 0.0000043 };  // 1 / (65 × 3600)
    case "GEN2":  { 0.0000079 };  // 1 / (35 × 3600)
    case "GEN1":  { 0.0000111 };  // 1 / (25 × 3600)
    default       { 0.0000174 };
};
private _gainRatio = _gain / _sensitivity max 0.01;
// Battery derating is wired from the physiology module (Issue #36) so
// the NVG drain and the physiological battery model share one factor.
// The physiology module publishes a capacity multiplier in the range
// 0.3-1.0.  The drain needs a drain multiplier: less capacity = faster
// drain, so invert.  At 0.3 derating (cold), drain is x3.3; at 1.0
// (normal), drain x1.  The factor is clamped to 1.0-4.0.
private _physDerating = missionNamespace getVariable [QEGVAR(physiology,batteryTemperatureDerating), 1.0];
if !(_physDerating isEqualType 0) then { _physDerating = 1.0; };
private _tempDrainFactor = if (_physDerating > 0.01) then { 1 / _physDerating } else { 3.0 };
_tempDrainFactor = _tempDrainFactor max 1.0 min 4.0;
private _drain = _baseDrain * _gainRatio * _tempDrainFactor * diag_deltaTime;
_battery = (_battery - _drain) max 0;
missionNamespace setVariable [QGVAR(nvgBattery), _battery];

// Degradation effects below thresholds.
// Below 0.3: noise floor rises by up to 2× (MCP bias low → excess noise).
if (_battery < 0.3) then {
    private _batteryNoisePenalty = (1 - _battery / 0.3) * 2;
    _noise = (_noise + _batteryNoisePenalty * 0.15) min 1;
};

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
private _glowPos = [0, 0, 0];   // world pos of the brightest source this tick
private _glowIntensityNow = 0;
{
    private _sim = getText ((configOf _x) >> "simulation");
    private _isBright = false;
    if (_sim == "Lamps" || _sim == "nvmarker") then { _isBright = true; };
    if (isLightOn _x) then { _isBright = true; };
    if (_x isKindOf "F_40_White") then { _isBright = true; };
    if (_isBright) then {
        private _srcPos = getPosASL _x;
        private _dirTo = _eye vectorFromTo _srcPos;
        private _ang = acos ((_viewDir vectorDotProduct _dirTo) max -1 min 1);
        // Occlusion: the light must physically reach the photocathode.
        // A lamp behind a wall cannot gate a real tube — the photons are
        // absorbed.  (The previous model assumed every source in the cone
        // contributes regardless of what is between it and the eye, which
        // gated through walls and caused the flicker.)  The eye-to-source
        // ray must be clear of blocking geometry.
        private _clear = true;
        private _occHits = lineIntersectsSurfaces [
            _eye, _srcPos, _player, _x, true, 1, "FIRE", "NONE"
        ];
        if (count _occHits > 0) then { _clear = false; };
        // Gate triggers when the source enters the tube's FOV.  AN/AVS-9
        // FOV is 40° circular (DTIC ADA426388, NASA 20030063076, Elbit
        // datasheet) — half-angle 20°.  Hysteresis: trigger at 20° but
        // only release beyond 25°, so a trembling hand or slow pan does
        // not flicker the gate at the cone edge.  The tube "remembers"
        // the source while it is near the FOV edge.
        private _gateHalf = 20;
        private _releaseHalf = 25;
        if (_clear && _ang < _releaseHalf) then {
            // Inverse-square illuminance at the photocathode, normalised
            // so a dead-centre source at 10 m is ~1.0.  The gate scales
            // with the light that actually reaches the tube.  Within the
            // hysteresis band (20-25°) the intensity fades to a floor so
            // the release is continuous, not a hard on/off.
            //
            // Beer-Lambert extinction: rain and fog scatter photons before
            // they reach the photocathode.  A source at 50 m through heavy
            // rain is dimmer than the same source in clear air — the tube
            // gates less aggressively.  This matches real NVG behaviour:
            // bad weather reduces auto-gating because less light reaches
            // the tube.
            private _dist = _eye distance _srcPos;
            private _rainExt = if (rain > 0.1) then { rain * 30 / 4343 } else { 0 };
            private _fogExt = if (fog > 0.3) then { (fog / 0.5) ^ 2 * 40 / 4343 min 300 / 4343 } else { 0 };
            private _extinction = _rainExt + _fogExt;
            private _transmission = if (_extinction > 0) then { exp (-_extinction * _dist) } else { 1 };
            private _coneScale = if (_ang < _gateHalf) then {
                (1 - _ang / _gateHalf)
            } else {
                0.05 * (1 - (_ang - _gateHalf) / (_releaseHalf - _gateHalf));
            };
            private _intensity = _coneScale * (100 / (_dist * _dist)) * _transmission;
            if (_intensity > _blowoutNow) then {
                _blowoutNow = _intensity;
                _glowPos = _srcPos;
                _glowIntensityNow = _intensity;
            };
        };
    };
} forEach _brightSources;

// ─── Rain: Mie scattering + auto-gating feedback loop ────────────────────
// Forward-scattered light from rain can trigger auto-gating even without
// a direct bright source.  The MCP detects the bright foreground scatter
// and reduces gain globally, making distant targets invisible while the
// foreground rain is still bright — the "white wall" effect.
// Model: heavy rain adds a minimum blowout floor.  At rain > 0.5, the
// scatter is bright enough to partially gate.  At rain > 0.8, the gate
// is effectively locked on (the gain reduction makes the image unusable
// anyway for distant targets).
if (rain > 0.5) then {
    private _rainGateFloor = (rain - 0.5) * 2;   // 0 at rain=0.5, 1 at rain=1.0
    _blowoutNow = _blowoutNow max (_rainGateFloor * 0.6);
};

// ─── Phosphor burn-in / afterimage (spatial) ─────────────────────────────
// The residual lag above handles the tube's CONTINUOUS response.  Burn-in
// is the SPATIAL ghost: a bright source imaged on the phosphor leaves a
// lingering glow at that screen position after the source leaves or the
// gate releases.  P20 (Gen 1/2) total persistence ~60 ms; P43/P45
// (Gen 3/PVS-31) ~2.6 ms — effectively instant.  Model: remember the
// last bright source's world position and intensity; when the live source
// drops, the stored glow decays per the phosphor persistence constant.
// GEN3/PVS31 afterimages are sub-tick and invisible; only GEN1/2 show a
// visible afterimage (~1 tick at 100 ms frame rate).
private _burnPos = missionNamespace getVariable [QGVAR(nvgBurnPos), [0, 0, 0]];
private _burnInt = missionNamespace getVariable [QGVAR(nvgBurnInt), 0];
if (_burnInt isEqualType 0) then {
    if (_glowIntensityNow > 0) then {
        _burnPos = _glowPos;
        _burnInt = _glowIntensityNow;
    } else {
        // Decay per phosphor persistence: alpha = exp(-dt/tau).  GEN1/2
        // P20 ~60 ms => at 0.1 s tick, alpha ≈ exp(-0.1/0.06) ≈ 0.19,
        // so the afterimage is visible for ~1 tick then gone.  GEN3/PVS31
        // P43/P45 ~2.6 ms => alpha ≈ 0 (instant, never visible).
        private _tau = [0.003, 0.06] select ((_tier == "GEN1") || (_tier == "GEN2"));
        _burnInt = _burnInt * exp (-(0.1 / _tau));
        if (_burnInt < 0.02) then { _burnInt = 0; };
    };
} else {
    _burnInt = _glowIntensityNow;
    _burnPos = _glowPos;
};
missionNamespace setVariable [QGVAR(nvgBurnPos), _burnPos];
missionNamespace setVariable [QGVAR(nvgBurnInt), _burnInt];

// Muzzle flash / explosive flash: the fired event stamps nvgFlashUntil.
if (CBA_missionTime < (missionNamespace getVariable [QGVAR(nvgFlashUntil), -1])) then {
    _blowoutNow = _blowoutNow max 0.9;
};

// Exponential envelope: instant attack, slow tier-dependent release with
// hold time.  Real auto-gating has a recovery period — the tube does not
// snap back the instant the source leaves the FOV.  Hold time prevents
// oscillation at the FOV cone edge (source flickering in/out at 20°).
// GEN1/GEN2: no gating, bloom persists longer (phosphor saturation).
// GEN3/PVS31: gated, fast recovery but with a hold to prevent flicker.
private _release = switch (_tier) do {
    case "GEN1": { 0.15 };   // ~7 s to fade (phosphor saturation)
    case "GEN2": { 0.25 };   // ~4 s to fade
    default { 0.50 };         // gated: ~2 s, with hold prevents edge flicker
};
private _holdTime = switch (_tier) do {
    case "GEN1": { 1.5 };    // long hold, bloom persists
    case "GEN2": { 0.8 };
    default { 0.4 };          // gated: 400 ms hold before decay starts
};
private _blowout = missionNamespace getVariable [QGVAR(nvgBlowout), 0];
private _blowoutHold = missionNamespace getVariable [QGVAR(nvgBlowoutHold), 0];
if (_blowout isEqualType 0) then {
    // Attack: instant (blowout spikes immediately when source enters cone).
    _blowout = _blowout max _blowoutNow;
    // Hold: once triggered, maintain peak for _holdTime seconds.
    if (CBA_missionTime < _blowoutHold) then {
        _blowout = _blowout max (_blowoutNow max _blowout);
    } else {
        // Decay: exponential release after hold expires.
        _blowout = _blowout * (1 - _release);
    };
    // When a new peak is detected, reset the hold timer.
    if (_blowoutNow > _blowout * 0.9) then {
        missionNamespace setVariable [QGVAR(nvgBlowoutHold), CBA_missionTime + _holdTime];
    };
} else {
    _blowout = _blowoutNow;
    missionNamespace setVariable [QGVAR(nvgBlowoutHold), CBA_missionTime + _holdTime];
};
if (_blowout < 0.01) then { _blowout = 0; };
missionNamespace setVariable [QGVAR(nvgBlowout), _blowout];
// Note: nvgBlowoutHold is set inside the if-blocks above.
// Do NOT overwrite it here with the stale local _blowoutHold.

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

// ─── Rain: Mie scattering volume effect ──────────────────────────────────
// Rain drops don't just sit on the lens — they create a 3D volume of
// forward-scattered light (Mie scattering: particles > wavelength scatter
// predominantly forward).  This scattered light enters the objective from
// all angles, creating a uniform veil that crushes SNR.  The MCP amplifies
// this scattered light equally with the signal, producing the "white wall"
// effect: foreground rain is amplified to blindness while distant targets
// disappear.  No existing mod simulates this — they all treat rain as a
// visual overlay.
//
// Scale contrast and MTF by rain intensity.  Heavy rain (0.8) drops MTF
// to 50% of clear-air value — the image degrades from sharp to mushy.
// This is separate from the localized drops on the lens (Mie is a
// volume effect, drops are a surface effect).
if (rain > 0.2) then {
    private _mieFactor = 1 - rain * 0.5;   // heavy rain: 60% MTF
    _mtfEffective = _mtfEffective * _mieFactor;
};

// ─── Rain: veiling glare amplification ───────────────────────────────────
// Each rain drop scatters light inside the tube (internal reflections
// between phosphor screen and photocathode).  This adds veiling glare —
// a uniform glow that reduces contrast.  Veiling glare is already a
// problem in clear conditions; rain makes it significantly worse because
// each drop creates additional scatter sources.
// Scale bloom by (1 + rain × 2).  Interacts with the existing bloom
// system — rain effectively doubles the halo contribution.
//
// Halo geometry: the halo is MCP electron scatter + phosphor bloom, and
// its radius grows with the photon flux on the tube face.  The blowout
// state (_blowout) already encodes inverse-square illuminance — a
// dead-centre source at 10 m is ~1.0, falling with distance² and
// atmospheric extinction (Beer-Lambert).  So a closer or brighter source
// produces a larger halo; ambient moonlight sets the base halo and the
// source term rides on top.
private _bloom = _bloomBase + _bloomScale * (_moonLight / 1.0);
_bloom = _bloom + _blowout * _bloomScale * 2;
_bloom = _bloom * (1 + rain * 2);
// Clear-condition veiling glare floor: phosphor light reflects back to the
// photocathode and re-amplifies, giving a real tube a 2-5 % veiling glare
// ratio even in perfect weather.  This caps maximum contrast (a faint glow
// over the whole image) and is independent of rain.  0.02 = 2 %, the low
// end of the published range, so it adds the physical floor without
// washing the image out.
_bloom = _bloom + 0.02;
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

// ─── Phosphor persistence (residual image lag) ────────────────────────────
// The phosphor screen does not emit instantly nor cut off instantly: it
// has a persistence time constant.  Per-tier from datasheets:
//   P20 (Zn,Cd)S:Ag — Gen 1/2 green: 90%→10% in 4 ms, total ~60 ms decay
//   P43 Gd₂O₂S:Tb   — Gen 3 green:  90%→10% in 1 ms, total ~2.6 ms
//   P45 Y₂O₂S:Tb    — PVS-31 white: ~2.6 ms (same as P43)
// (Proxivision PR-0069E-02, Hoess & Fleder, Night Vision Wiki)
// At a 0.1 s tick the EMA alpha = 1 - exp(-dt/tau):
//   GEN1/2:  1 - exp(-0.1/0.06) ≈ 0.81 (fast settle — most lag is in the
//            first tick; the phosphor is fully decayed within 0.1 s)
//   GEN3/31: 1 - exp(-0.1/0.003) ≈ 1.0 (instant — phosphor is already
//            gone before the next tick)
// GEN3 lag is therefore negligible and only GEN1/2 benefit from this EMA.
private _phosphorTau = [0.003, 0.06] select ((_tier == "GEN1") || (_tier == "GEN2"));
private _phosphorAlpha = 1 - (exp (-(0.1 / _phosphorTau)));
private _brightLag = missionNamespace getVariable [QGVAR(nvgBrightLag), _brightness];
if (_brightLag isEqualType 0) then {
    _brightLag = _brightLag + (_brightness - _brightLag) * _phosphorAlpha;
} else {
    _brightLag = _brightness;
};
missionNamespace setVariable [QGVAR(nvgBrightLag), _brightLag];
if (_tier == "GEN1" || _tier == "GEN2") then {
    _brightness = _brightLag;
};

// ─── Auto-gating flicker (~30 kHz aliased) ───────────────────────────────
// Real auto-gating tubes cycle the MCP gain on/off at ~30 kHz (DTIC
// ADA426388, Elbit datasheet).  At 60 fps the 30 kHz is far above the
// flicker-fusion threshold (~60 Hz) — the temporal pattern is below
// human perception.  The physical effect is imperceptible flicker;
// it cannot be faithfully simulated at frame-rate frequencies without
// creating visible aliasing artifacts (a 30 kHz sin aliased to 60 fps
// produces a ~35 Hz beat, which IS visible and annoying).
// SKIP: no sin modulation.  The existing dynamic brightness variation
// from AGC settling and blowout recovery already provides enough
// temporal texture.  Adding a fake low-frequency shimmer would be less
// accurate than doing nothing.

// ─── Battery brightness degradation (after _brightness defined) ──────────
// These effects modify _brightness, which is defined at line ~567.
// Split from the noise degradation above to respect variable scope.
// Below 0.15: subtle horizontal scan-line flicker (MCP bias instability).
if (_battery < 0.15) then {
    private _flickerAmp = (1 - _battery / 0.15) * 0.08;
    _brightness = _brightness * (1 + _flickerAmp * sin (diag_tickTime * 120));
};
// Below 0.05: intermittent dropout — random black frames (voltage
// intermittently too low to sustain the MCP cascade).
if (_battery < 0.05 && {random 1 < 0.15}) then {
    _brightness = 0;
};

// ─── FilmGrain parameters (shot noise) ───────────────────────────────────
// Grain sharpness and size scale with noise level.  At high noise
// (starlight), grain is coarse and sharp.  At low noise (full moon),
// grain is fine and soft.  Ranges follow ACE3 (ST_NVG_NOISESHARPNESS_*
// 1.0-1.2, ST_NVG_GRAIN_* 2.25-2.7).  Monochromatic = 0 (grayscale grain:
// BIS wiki states 0 = monochrome, any other value = colour).  Grayscale
// suits both P45 white and P43 green phosphor (tube scintillation is
// monochrome).
//
// ENGINE LIMITATION: spatial scintillation variation (less noise in bright
// areas, more in dark — Poisson SNR ∝ √signal) cannot be implemented.
// FilmGrain applies uniform noise across the screen; no per-pixel
// weighting is available without a custom pixel shader.  The _noise
// variable already varies with ambient light (starlight → more noise
// everywhere, full moon → less), which is the correct macro-level
// behaviour.  Per-frame spatial variation is the honest wall.
private _sharpness = linearConversion [1, 0, _noise, 1.2, 1.0, true];
private _grainSize = linearConversion [1, 0, _noise, 2.7, 2.25, true];

// Scintillation intensity scales with ambient lux: maximum in darkness
// (few photons = strong shot noise), minimum in moonlight (many photons
// = quiet image).  Rain adds forward-scattered photon noise (Mie), so
// the grain rises with rain too.
private _grainIntensity = 0.3 * (1 - _lux / 0.1);
_grainIntensity = 0 max _grainIntensity;
_grainIntensity = _grainIntensity * (1 + rain * 0.5);

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
    // One INFO line per entry so a failed create (-1) is visible without
    // the per-tick debug flag: the essential handles must all be >= 0 or
    // the image degrades to vanilla and the adjusts spam the RPT.
    private _logMsg = format ["NVG handles created: vig=%1 bloom=%2 cc=%3 grain=%4 chroma=%5", _hVig, _hBloom, _hCC, _hGrain, _hChroma];
    AEE_LOG_INFO(_logMsg);
};

// Re-read the handles from missionNamespace at FUNCTION scope.  The
// `_handles params` above runs inside the if-block, whose scope shadows
// the function-scope locals — the adjust section below would otherwise
// read the stale -1 values and throw "Invalid post effect handle" on
// every fresh handle (4 handles x 4 calls = the 16 per entry seen in the
// RPT).  missionNamespace is the single source of truth; always read it
// after the create block.
_hVig   = missionNamespace getVariable [QGVAR(ppHandle_NVG_Vignette), -1];
_hBloom = missionNamespace getVariable [QGVAR(ppHandle_NVG_Bloom), -1];
_hCC    = missionNamespace getVariable [QGVAR(ppHandle_NVG_CC), -1];
_hGrain = missionNamespace getVariable [QGVAR(ppHandle_NVG_Grain), -1];

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
// Params follow TFN's proven values: blur 1..10 (5 default), focus distance
// in metres (7 default), third value 1.  Blur sign flips near/far in TFN
// (negative = far focus); we use negative for far, positive for near and
// flip by how the player's look distance relates to the focus plane.
// Tiers get different blur strengths: Gen 1/2 objective blurs more than
// filmless Gen 3/4 (deeper depth of field).
// Focus distance from a FAN of raycasts across the target area.
// Single-ray focus is wrong twice over: the centre ray slips past low
// objects (a 0.5 m sandbag at eye height is missed, a taller bush is
// hit), and any gap between clustered objects shoots the focus to the
// 300 m background.  A tight fan around the view vector returns the
// NEAREST surface in the target area, so a close cluster holds focus
// instead of snapping away and back.
//
// Geometry mode FIRE: hits everything with bullet collision - sandbags,
// bushes, walls, terrain.  GEOM missed the low sandbag in testing.
//
// Fan spread is SCREEN-SPACE, not a fixed world angle: it covers ~15 % of
// the player's horizontal view, the central region the eye actually
// focuses on.  A fixed 6 deg world angle is wrong on ultrawide (21:9)
// where 15 % of screen is ~14.7 deg, and too wide on 4:3 where it is
// ~6.8 deg.  Convert via the player's aspect ratio:
//   tan(hFOV/2) = tan(vFOV/2) * aspect,  vFOV from fovTop (0.75 default)
//   focus_half = atan(tan(hFOV/2) * 0.15)
// getResolution #4 = screen aspect (width/height).  Fall back to 16:9
// if the query returns 0 (headless or pre-init).
private _eyePos = eyePos _player;
// vectorDirVisual = where the EYES look (free-look / head direction).
// vectorDir would be the body direction - free-looking at a lamp post
// would not move the focus fan.  The fan must track the eye, the same
// as the blowout cone at line 304.
private _lookDir = vectorDirVisual _player;
private _aspect = getResolution select 4;
if (_aspect <= 0) then { _aspect = 16.0 / 9.0; };
// Live camera FOV via CBA (ACE3-proven): returns [hFOV, zoom] for the
// CURRENT view, so it follows the player's FOV slider, weapon zoom, and
// borderless-window aspect changes.  A static fovTop from config ignores
// all three.  Fall back to the config value if CBA is absent (should not
// happen - AEE requires CBA).
private _cbaFov = [1.0, 0.0];
if !(isNil "CBA_fnc_getFov") then { _cbaFov = [1.0] call CBA_fnc_getFov; };
_cbaFov params ["_hFovLive", "_zoomLive"];
if (_hFovLive <= 0) then {
    // Fallback: horizontal FOV from fovTop config + aspect.
    private _fovTop = getNumber (configFile >> "CfgDifficulties" >> "Base" >> "fovTop");
    if (_fovTop <= 0) then { _fovTop = 0.75; };
    _hFovLive = atan ((tan (atan _fovTop)) * _aspect);
};
private _focusHalfDeg = atan ((tan _hFovLive) * 0.15);   // 15 % of screen
private _spread = 300 * (tan _focusHalfDeg);      // offset at the 300 m end
private _upVec   = vectorUp _player;
private _rightVec = _lookDir vectorCrossProduct _upVec;
// ─── Fan raycast, CENTRE-DECISIVE weighted median ────────────────────────
// What the operator LOOKS AT (the centre ray) must win.  The research
// (O3DE auto-focus) uses a single centre sample; the fan exists only to
// catch low objects the centre misses and to average.  Weights are
// therefore centre-DECISIVE: one centre hit (weight 16) beats all eight
// background rays (2 each cardinal, 1 each diagonal = 12 total), so
// looking at an object focuses it even when the surrounding scene is
// farther.  Zoom no longer needed to make the object fill the fan.
//
// Gaussian-like falloff from centre: 16 / 2 / 1 (centre/cardinal/diag).
private _hitsArr = [];
private _fan = [
    [_lookDir, 16],
    [_lookDir vectorAdd (_upVec vectorMultiply _spread), 2],
    [_lookDir vectorAdd (_upVec vectorMultiply (-_spread)), 2],
    [_lookDir vectorAdd (_rightVec vectorMultiply _spread), 2],
    [_lookDir vectorAdd (_rightVec vectorMultiply (-_spread)), 2],
    [_lookDir vectorAdd ((_upVec vectorAdd _rightVec) vectorMultiply _spread), 1],
    [_lookDir vectorAdd ((_upVec vectorAdd _rightVec) vectorMultiply (-_spread)), 1],
    [_lookDir vectorAdd ((_upVec vectorAdd _rightVec vectorMultiply (-1)) vectorMultiply _spread), 1],
    [_lookDir vectorAdd ((_upVec vectorAdd _rightVec vectorMultiply (-1)) vectorMultiply (-_spread)), 1]
];
private _veh = vehicle _player;
{
    _x params ["_rayDir", "_rayWeight"];
    private _end = _eyePos vectorAdd (_rayDir vectorMultiply 300);
    private _hits = lineIntersectsSurfaces [
        _eyePos, _end, _player, objNull, true, 1, "GEOM", "NONE"
    ];
    private _hitDist = -1;
    if (count _hits > 0) then {
        private _d = _eyePos distance (_hits select 0 select 0);
        // Weapon/hands/vehicle exclusion by OBJECT IDENTITY, not distance.
        // The weapon, body and the vehicle cabin are part of the operator's
        // own model - a real NVG operator focuses PAST their own gear and
        // through the windshield, not on the interior.  Object identity
        // lets a REAL wall at 1 m track down to the objective's ~25 cm
        // near limit, so the DoF band forms the gradual blur gate.
        private _hitObj = _hits select 0 select 2;
        private _hitParent = _hits select 0 select 3;
        if (_hitObj != _player && _hitParent != _player
            && _hitObj != _veh && _hitParent != _veh) then {
            _hitDist = _d;
        };
    };
    // lineIntersectsSurfaces is unreliable for terrain (ground) hits.
    // For rays pointing down that missed an object, compute the ground
    // distance analytically.  The ray must be UNIT length for the Z
    // component to be a direction cosine: the fan rays are lookDir plus
    // a ~26 m offset at the 300 m end, so their magnitude is ~26, NOT 1.
    // Using the raw Z would make every offset ray's distance ~26x too
    // small.  getTerrainHeightASL is a cheap heightmap lookup, not a
    // raycast.  Sky (ray pointing up) contributes no hit, so
    // HOLD-ON-EMPTY keeps the ring where it is.
    private _rd = vectorNormalized _rayDir;
    private _rdZ = _rd select 2;
    if (_hitDist < 0 && _rdZ < -0.01) then {
        private _eyeH = _eyePos select 2;
        // First estimate: the flat plane at the terrain height below the
        // eye.  Exact on level ground; the iteration below corrects for
        // slopes (ground ahead higher or lower than below the eye).
        private _tDist = (_eyeH - getTerrainHeightASL _eyePos) / abs _rdZ;
        // Fixed-point correction: re-solve t = (eye_h - terrain_h(sample))
        // / |dz| at the current estimate.  This is the exact ray-plane
        // solve repeated on the REAL terrain height, so it converges on
        // slopes (ground ahead higher or lower than below the eye) where
        // a single flat-plane step is wrong by the slope ratio.  The
        // factor is < 1 whenever the ray descends faster than the terrain
        // rises toward it; a grazing ray that the terrain outruns pushes
        // t past the 300 m cap and correctly reads as no hit.
        for "_i" from 1 to 4 do {
            private _sample = _eyePos vectorAdd (_rd vectorMultiply _tDist);
            private _sampleH = getTerrainHeightASL _sample;
            private _rayH = _eyeH + _rdZ * _tDist;
            private _err = _sampleH - _rayH;
            if (abs _err < 0.3) exitWith {};
            _tDist = (_eyeH - _sampleH) / abs _rdZ;
            if (_tDist <= 0.25) exitWith {};
        };
        if (_tDist > 0.25 && _tDist <= 300) then {
            _hitDist = _tDist;
        };
    };
    if (_hitDist > 0) then {
        _hitsArr pushBack [(_hitDist max 0.25), _rayWeight];
    };
} forEach _fan;

private _rawTarget = 0;
if (count _hitsArr >= (count _fan) / 2) then {
    // Sort by distance, expand by weight, take the weighted median.
    // Weights are small ints (16/2/1) so the expansion is cheap.
    _hitsArr sort true;
    private _weighted = [];
    {
        _x params ["_d", "_w"];
        for "_i" from 1 to _w do { _weighted pushBack _d; };
    } forEach _hitsArr;
    _rawTarget = _weighted select (floor ((count _weighted) / 2));
};

// ─── Raw-target smoothing (ROLLING MEDIAN) ────────────────────────────────
// The median of a 9-ray fan is noisy: the scene composition shifts tick to
// tick as the view moves fractions of a degree, so the median jumps 1-3 m
// between ticks — and worse, a single tick can bounce it 12 m -> 137 m
// when the centre ray slips past a low object to the background or a
// sub-degree head shift crosses the horizon.  The OLD conditional EMA
// passed every "big" change straight through, so with 12<->137 bouncing
// it smoothed NOTHING: the state machine saw a fresh target every tick,
// re-armed the 0.2 s hold clock continuously, and the ring sat frozen
// until the raw went quiet for a moment — the "sticky then jump" the
// user reported.
//
// A rolling MEDIAN of the last 3 raw samples is the fix: a single-tick
// outlier (137) is discarded, a genuine sustained re-aim (12 m for 3+
// ticks) tracks within 3 ticks.  This is what a real autofocus does —
// integrate over time, not chase each frame.  Measured on RPT data:
// the median kills every single-tick outlier while the EMA passed all
// of them through.
private _rawHist = missionNamespace getVariable [QGVAR(nvgFocusRawHist), []];
if !(_rawHist isEqualType []) then { _rawHist = []; };
if (_rawTarget > 0) then {
    _rawHist pushBack _rawTarget;
    if (count _rawHist > 3) then { _rawHist deleteAt 0; };
} else {
    _rawHist = [];   // sky: empty the history so HOLD-ON-EMPTY stays clean
};
missionNamespace setVariable [QGVAR(nvgFocusRawHist), _rawHist];
private _rawSmooth = _rawTarget;
if (count _rawHist > 0) then {
    private _sorted = +_rawHist;
    _sorted sort true;
    _rawSmooth = _sorted select (floor ((count _sorted) / 2));
};
if (_rawSmooth <= 0) then { _rawSmooth = _rawTarget; };
_rawTarget = _rawSmooth;

// ─── Focus state machine (O3DE auto-focus pattern) ───────────────────────
// The raw fan distance still snaps: looking at sky returns no hit, and a
// bush grazing the centre pixel drags the target for a tick.  O3DE's
// DepthOfFieldReadBackFocusDepthPass is the canonical anti-breathing
// design, and the physics is the real NVG objective: a MANUAL ring with
// 25 cm->infinity travel, hyperfocal ~12-24 m (f/1.2, 27 mm, CoC
// 25-50 um).  We reproduce that mechanism, not a camera autofocus:
//
//  1. HOLD-ON-EMPTY: no ray hit (sky) keeps the current focus.  A real
//     ring does not fly to infinity when you look up; it stays where you
//     set it.  This kills the "snaps away and back" artefact.
//  2. DEADBAND: do not move while |target - current| < deadband.
//     Hyperfocal behaviour: at focus distance F, objects within the DoF
//     band are acceptably sharp, so the ring should not hunt for them.
//     Deadband = 3 % of current focus, min 0.5 m.
//
//     CALIBRATION (measured, not guessed): the RPT focus fan reads a
//     noise floor of sigma = 0.2-0.3 % of the target distance on a
//     STABLE scene (measured: 0.06 m at 28 m, 0.36 m at 125 m).  The
//     classic contrast-AF controller deadband (Sanyo EP0437629B1) is a
//     threshold on the focus measure sized to reject measurement noise.
//     The distance deadband must sit ABOVE that noise floor but track
//     real changes: 3 % is 10-15x the measured sigma.  The previous
//     25 % was 80x the noise floor — it demonstrably froze the ring on
//     a genuine 28 m -> 35 m re-aim (the "too sticky" report).  The
//     re-arm threshold below scales with it.
//  3. DELAY: hold a new target 0.25 s before moving, so a transient hit
//     (a branch passing the centre pixel) does not rack the ring.
//  4. CONSTANT SPEED: the ring turns at a fixed rate while you move it.
//     15 m/s lens-group travel: a 5 m shift (sandbag to bush) settles in
//     ~0.3 s, a 100 m shift glides over ~7 s.  Slower than before
//     (40 m/s) so a large rack reads as a deliberate ring turn, not a
//     snap.  Snap when within one step.
//
// State persists in missionNamespace: current focus, pending target and
// its hold-until time.
// Cold start: the ring sits at the device's hyperfocal default, NOT at
// the first fan target.  On the first tick the fan often reads the far
// background (the eye hasn't settled on anything yet), which used to
// initialise focus at ~300 m and then glide down for several seconds -
// the "starts off at 300m" the user saw.  The device default is where a
// real operator's ring sits when they first put the goggles on.
private _dofInitialised = missionNamespace getVariable [QGVAR(nvgFocusInit), false];
private _curFocus = missionNamespace getVariable [QGVAR(nvgFocusCur), _dofDefaultDist];
private _pending  = missionNamespace getVariable [QGVAR(nvgFocusPending), 0];
private _holdUntil = missionNamespace getVariable [QGVAR(nvgFocusHoldUntil), 0];
if !(_curFocus isEqualType 0 && _curFocus > 0) then { _curFocus = _dofDefaultDist; };
if (!_dofInitialised) then {
    _curFocus = _dofDefaultDist;
    missionNamespace setVariable [QGVAR(nvgFocusInit), true];
};

if (_rawTarget > 0) then {
    private _deadband = (_curFocus * 0.03) max 0.5;
    if (abs (_rawTarget - _curFocus) > _deadband) then {
        // Outside the sharp band: arm a new target.  Re-arm (reset the
        // hold timer) only when the target CHANGES MATERIALLY - a
        // movement-induced sweep (walking parallax moves the median 1-3 m
        // per tick) must NOT re-arm every tick, or the focus racks
        // constantly while moving (measured: 20 % of ticks had focus
        // moving with a stable raw).  The re-arm threshold scales with
        // the deadband: small at close focus, proportional at distance.
        if (_rawTarget != _pending) then {
            private _rearm = _deadband * 0.4;
            if (_pending == 0 || abs (_rawTarget - _pending) > _rearm) then {
                _pending = _rawTarget;
                _holdUntil = CBA_missionTime + 0.2;   // transient rejection
            } else {
                _pending = _rawTarget;   // follow drift, keep the clock
            };
        };
    } else {
        // Inside the band: the ring does not move.  Cancel a PENDING
        // target only when no rack is in flight.  (An in-flight rack
        // must continue to its target - cancelling mid-rack is what
        // left the focus stranded short, found by validate_dof.py's
        // glide check.)
        if (_pending == 0) then {
            _holdUntil = 0;
        };
    };
};

if (_pending > 0 && CBA_missionTime >= _holdUntil) then {
    // ─── Lens rack in LENS-TRAVEL space (constant ring angular rate) ─────
    // A real NVG objective is a smooth helical focus ring, ~270 deg over
    // the full throw, no detent (friction-held).  The operator turns it
    // at a roughly CONSTANT angular velocity; the cam maps angle to lens
    // travel LINEARLY.  Focus distance is NOT linear in lens travel:
    // thin lens 1/f = 1/s + 1/s' -> lens travel x = f^2/(s-f) for
    // object distance s (f = 27 mm objective, ATN PVS-14 spec).
    //
    //   s = 0.25 m -> x = 3.3 mm   (throw near end)
    //   s = 3 m    -> x = 0.24 mm
    //   s = 143 m  -> x = 0.005 mm
    //
    // So a constant x-rate sweeps focus distance NON-linearly: fast at
    // distance (tiny x covers huge s), slow up close (most of the throw
    // is the 0.25-3 m region).  That is the real feel: near->far, the
    // ring sweeps the near region slowly then "reaches" the far setting;
    // far->near, the first tick jumps the focus far before settling.
    //
    // Rack speed: a deliberate full-range twist is ~0.5 s (0.3-1 s
    // bracket, forum-sourced).  The throw (x range) is device-specific:
    // x_throw = f^2/(near-f), so PVS-14 (0.25 m near) is 3.3 mm and
    // PVS-31A/GPNVG (0.45 m near) is ~1.7 mm - the GPNVG ring is finer
    // per degree.  xStep per 0.1 s tick = throw / 5 (full range in 0.5 s).
    private _focalLen = 0.027;                            // objective f, m
    private _f2 = _focalLen * _focalLen;                  // 0.000729
    private _xNow = _f2 / (_curFocus - _focalLen);
    private _xTgt = _f2 / (_pending - _focalLen);
    private _throw = _f2 / (_dofNearLimit - _focalLen);   // device throw
    private _xStep = _throw / 5;                          // ~0.5 s full range
    private _xMove = _xTgt - _xNow;
    if (abs _xMove > _xStep) then {
        _xMove = _xStep * ([1, -1] select (_xMove < 0));
    };
    private _xNew = _xNow + _xMove;
    _curFocus = _focalLen + _f2 / _xNew;
    if (abs (_pending - _curFocus) < 0.1) then {
        _curFocus = _pending;           // settle exactly
        _pending = 0;
        _holdUntil = 0;
    } else {
        // ─── Settle watchdog ─────────────────────────────────────────
        // Guarantee against a stuck ring: if a target has been pending
        // for over 1.5 s and the rack is still in flight, the ring is
        // not making progress — snap it to the target.  This is the
        // absolute bound: no input sequence can freeze the focus
        // indefinitely, because any pending target that outlives the
        // watchdog is applied in full.  A real autofocus has the same
        // timeout (a servo that stops reporting progress is reset).
        if (CBA_missionTime > (_holdUntil + 1.5)) then {
            _curFocus = _pending;
            _pending = 0;
            _holdUntil = 0;
        };
    };
};

missionNamespace setVariable [QGVAR(nvgFocusCur), _curFocus];
missionNamespace setVariable [QGVAR(nvgFocusPending), _pending];
missionNamespace setVariable [QGVAR(nvgFocusHoldUntil), _holdUntil];
// ─── Mode gate: MANUAL vs AUTO ───────────────────────────────────────────
// dofMode (missionNamespace, set by the actions keybind): 0 = AUTO (the
// O3DE state machine above), 1 = MANUAL (the player's ring position from
// the Focus In/Out keybinds).  Real NVGs are manual-focus (the ring sits
// at a hyperfocal distance and everything from the near limit to
// infinity is sharp); the ENVG family adds autofocus.  The DEFAULT is
// per-device (from the researched config above): most goggles start in
// MANUAL at their hyperfocal ring position; only the ENVG-II fusion
// goggle starts in AUTO.  In MANUAL the ring holds where the player set
// it - moving closer/further passes objects through the plane naturally.
private _dofModeSet = missionNamespace getVariable ["aee_optics_dofModeSet", false];
if (!_dofModeSet) then {
    missionNamespace setVariable ["aee_optics_dofMode", _dofModeDefault];
    missionNamespace setVariable ["aee_optics_dofModeSet", true];
};
private _dofMode = missionNamespace getVariable ["aee_optics_dofMode", _dofModeDefault];
private _focusDist = if (_dofMode == 1) then {
    private _manual = missionNamespace getVariable ["aee_optics_dofManualDist", _dofDefaultDist];
    _manual max _dofNearLimit min _dofMaxDist
} else {
    _curFocus max _dofNearLimit min _dofMaxDist
};
private _focusSettled = (_pending == 0);
private _dofBlur = switch (_tier) do {
    case "PVS31": { 3.0 };
    case "GEN3":  { 4.0 };
    case "GEN2":  { 6.0 };
    default      { 8.0 };   // Gen 1: shallow, hard-to-focus objective
};
if (_hDoF >= 0) then {
    // Blur is NEGATIVE, constant (TFN's far-focus default).  The sign
    // convention is unverified (research: the wiki marks DepthOfField
    // TBD; no primary source documents the param semantics), so a sign
    // flip would be a guess on top of a guess.  Worse, an auto-focus
    // that flips sign at a 10 m threshold SNAPS the blur +8 -> -8 the
    // instant the gliding focus crosses the boundary - the snapping the
    // user saw despite the smooth glide in the RPT.  Constant sign +
    // varying distance is a continuous function of focus; only the
    // distance param moves the focus plane.
    //
    // Commit 0.1 s: the focus moves ~1.5 m per 0.1 s tick, so each step
    // eases into the next instead of applying abruptly.  The glide in
    // the focus value is then matched by a glide in the rendered blur.
    _hDoF ppEffectAdjust [-_dofBlur, _focusDist, 1];
    _hDoF ppEffectCommit 0.15;
    _hDoF ppEffectEnable true;
    _hDoF ppEffectForceInNVG true;
};

// Diagnostics: set aee_optics_nvgDebug = true in the debug console to log
// every tick's handles and params to the .rpt.  ppEffectCreate returns -1
// when the priority is taken — a -1 handle means the effect did not apply.
// gain and lux are the AGC inputs: gain must fall as lux rises (the
// inverse-lux auto-gating response) — the two numbers prove the gate works.
if (missionNamespace getVariable [QGVAR(nvgDebug), false]) then {
    diag_log text format [
        "[AEE] NVG tick | tier=%1 moon=%2 lux=%3 gain=%4 visMode=%5 hmd=%6 | handles CC=%7 chroma=%8 bloom=%9 vig=%10 grain=%11 dof=%12 | CC params %13 | bloom=%14 grain=%15 | blowout=%16 | dofBlur=%17 focus=%18 settled=%19 raw=%20 pending=%21",
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
        [_grainIntensity, _sharpness, _grainSize, 0.5, 1.0, 0],
        _blowout,
        _dofBlur,
        _focusDist,
        _focusSettled,
        _rawTarget,
        _pending
    ];
};

// ─── ChromAberration — disabled (NVGs are monochrome) ────────────────────
// ponytail: NVGs are monochrome — no chromatic aberration.
// An image intensifier has a single photocathode and a single phosphor
// screen, so its output carries no colour fringing.  ChromAberration is
// a normal-vision effect (lens dispersion in a colour camera).  The
// handle is still created and owned by fnc_managePostProcess for normal
// vision; the NVG path leaves it neutral.  The per-tier _chromaStrength
// parameter is removed with the effect.
//
// Removed: the edge boost (1 + (angle/20)²) and the per-tick
// adjust/commit/enable/force block — with no CA there is nothing to
// scale or apply.
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
_hCC ppEffectCommit 0;
_hCC ppEffectEnable true;
_hCC ppEffectForceInNVG true;

// ─── DynamicBlur (blooming / halos from bright sources) ──────────────────
_hBloom ppEffectAdjust [_bloom];
_hBloom ppEffectCommit 0;
_hBloom ppEffectEnable true;
_hBloom ppEffectForceInNVG true;

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
_hVig ppEffectCommit 0;
_hVig ppEffectEnable true;
_hVig ppEffectForceInNVG true;

// ─── FilmGrain (shot noise - the NVG aesthetic) ──────────────────────────
_hGrain ppEffectAdjust [_grainIntensity, _sharpness, _grainSize, 0.5, 1.0, 0];
_hGrain ppEffectCommit 0;
_hGrain ppEffectEnable true;
_hGrain ppEffectForceInNVG true;

// ─── RscTitles display (focus HUD) ────────────────────────────────────────
// The engine handles the NVG cutout (circular tube view).  We overlay only
// the focus readout HUD.  No mask, fibre, glow, or rain overlay — the
// engine and other NVG mods handle tube geometry.
private _disp = uiNamespace getVariable [QGVAR(titleDisplay), displayNull];
if !(missionNamespace getVariable [QGVAR(nvgDisplayUp), false]) then {
    (["aee_optics_nvg_title"] call BIS_fnc_rscLayer) cutRsc [QGVAR(nvgTitle), "PLAIN", 1, false];
    missionNamespace setVariable [QGVAR(nvgDisplayUp), true];
};
if (!isNull _disp) then {
    // Focus readout (ECOTI HUD style): the ring position as metres plus a
    // 0-100 m scale bar with a marker at the current focus.  The bar is
    // logarithmic in display so the 0-25 m patrol band dominates; a 50 m
    // focus sits mid-bar.  In MANUAL mode this shows the ring value the
    // player set; in AUTO it shows where the state machine settled.
    private _focusDisp = _focusDist max 0.25;
    private _focusText = format ["FOCUS %1m", round _focusDisp];
    private _barPos = (log (_focusDisp + 1)) / (log 101);   // 0..1 over 0-100 m
    private _barLen = 24;
    private _marker = round (_barPos * _barLen);
    private _bar = "";
    for "_i" from 0 to _barLen do {
        _bar = _bar + (["-", "o"] select (_i == _marker));
    };
    private _focusCtl = _disp displayCtrl 1002;
    _focusCtl ctrlSetText _focusText;
    _focusCtl ctrlCommit 0;
    private _barCtl = _disp displayCtrl 1003;
    _barCtl ctrlSetText _bar;
    _barCtl ctrlCommit 0;

    // ─── Low-battery warning indicators ───────────────────────────────
    // Real PVS-31: red LED in each monocular when ≤10 min remain
    //   (L3Harris PVS-31A datasheet).
    // Real PVS-14 (GEN3): blinking eyepiece indicator when ≤30 min remain
    //   (TM 11-5855-306-10).
    // Calculate time remaining from battery level and current drain rate.
    private _currentDrainRate = _baseDrain * _gainRatio * _tempDrainFactor;
    private _timeRemaining = if (_currentDrainRate > 0) then {
        _battery / _currentDrainRate
    } else { 99999 };

    // PVS-31: steady red LED when ≤10 min (600 s) remaining.
    private _battWarnCtl = _disp displayCtrl 1004;
    if (_tier == "PVS31" && _timeRemaining <= 600) then {
        _battWarnCtl ctrlShow true;
    } else {
        _battWarnCtl ctrlShow false;
    };
    _battWarnCtl ctrlCommit 0;

    // GEN3: blinking "BATT" when ≤30 min (1800 s) remaining.
    // Blinks at ~2 Hz (toggle every 0.25 s).
    private _battBlinkCtl = _disp displayCtrl 1005;
    if (_tier == "GEN3" && _timeRemaining <= 1800) then {
        private _blinkOn = (floor (diag_tickTime * 4)) % 2 == 0;
        _battBlinkCtl ctrlShow _blinkOn;
    } else {
        _battBlinkCtl ctrlShow false;
    };
    _battBlinkCtl ctrlCommit 0;
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
