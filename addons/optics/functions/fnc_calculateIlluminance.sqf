#include "..\script_component.hpp"

/*
 * Shared illuminance layer — the single source of light data for every
 * module (NVG, thermal, glare, ballistics visibility).
 *
 * PRIMARY: getLighting (no-arg).  Returns [ambientColor, ambientBrightness,
 * lightDirection, starsVisibility].  Verified on a dedicated server (docker
 * probe): 4 elements, works headless.  lightDirection is the sun/moon
 * vector — the glare/thermal source.  ambientBrightness is FROZEN on a
 * headless server (the lighting engine only advances per-camera), so it
 * is NOT used as the lux source.
 *
 * LUX SOURCE: the validated moonIntensity/overcast/rain model (real engine
 * variables, time-varying on every machine).  Engine illuminance cannot
 * be sampled at night without a client camera (getLightingAt returns []
 * on a logic, frozen on headless, and is client-NV-dependent per tracker
 * T156930), so the physics lux model remains authoritative.
 *
 * DYNAMIC: getLightingAt needs a real UNIT (returns [] on a logic).  It
 * adds dynamic light-source lux on the client; skipped on the server.
 *
 * Outputs (missionNamespace, shared):
 *   aee_core_illuminanceLux     - total lux (moon model + client dynamic)
 *   aee_core_ambientLux         - ambient lux (moon model)
 *   aee_core_dynamicLux         - dynamic (light-source) lux, client only
 *   aee_core_lightDirection     - engine sun/moon unit vector (getLighting)
 *   aee_core_lightAzimuth       - compass azimuth of primary light, degrees
 *   aee_core_lightElevation     - elevation of primary light, degrees
 *   aee_core_lightIsNight       - true when the engine reports no sun
 *   aee_core_starsVisibility    - engine star visibility 0..1
 */

params [["_posASL", [0, 0, 0], [[]]]];

// ─── Primary: getLighting direction + stars (works everywhere) ───────────
private _lightDir = [0, 0, 1];
private _stars = 0;
private _lightGlobal = getLighting;
if (count _lightGlobal >= 4) then {
    private _dir = _lightGlobal select 2;
    _stars = _lightGlobal select 3;
    if (_dir isEqualType [] && {count _dir == 3}) then { _lightDir = _dir; };
};

// Convert the engine's sun/moon vector to azimuth/elevation (degrees).
// Arma's light direction is a world vector pointing FROM the light: x=east,
// y=south, z=up (Arma compass convention: north = -y).  Azimuth is measured
// clockwise from north (getDir convention).  Elevation is angle above
// horizon, 0 at horizon, 90 straight up.
private _lightAzimuth = 0;
private _lightElevation = 0;
private _lightLen = vectorMagnitude _lightDir;
if (_lightLen > 0.001) then {
    _lightElevation = asin ((_lightDir select 2) / _lightLen);
    private _flatX = _lightDir select 0;
    private _flatY = _lightDir select 1;
    private _flatLen = sqrt ((_flatX * _flatX) + (_flatY * _flatY));
    if (_flatLen > 0.001) then {
        // atan2-like: north (0, -1) → 0°, east (1, 0) → 90°
        private _ang = _flatX atan2 (-_flatY);
        _lightAzimuth = _ang mod 360;
        if (_lightAzimuth < 0) then { _lightAzimuth = _lightAzimuth + 360; };
    };
};

// ─── Lux: validated moonIntensity/overcast/rain model ────────────────────
// Engine ambient brightness is frozen on headless and camera-dependent, so
// the lux base comes from real engine weather variables (moonIntensity,
// overcast, rain) — time-varying and identical on every machine.
//
// moonIntensity is 0..1 and is the ENGINE's effective moon brightness
// (phase + elevation already folded in): ACE3's ambientBrightness uses it
// directly with no phase curve or elevation scaling, and its real-world
// anchor matches (full moon -> 0.25 lux, quarter -> ~0.02-0.03).
//
// Overcast: the engine does NOT attenuate moonIntensity for clouds — ACE3
// applies its own (1 - overcast) factor on the moon term.  Cloud cover is
// a multiplicative transmission loss, NOT an additive subtraction: heavy
// overcast blocks ~85 % of moonlight (ACE3 goes to 0 at full overcast;
// Garstang/Kyba show 80-90 % loss under thick cloud).  The old additive
// cap min(overcast*0.8, 0.275) limited the loss to 27.5 %, passing 72 % of
// moonlight through a storm — physically wrong.
// NOTE: min/max bind LOOSER than arithmetic in SQF, so the cap MUST be
// parenthesised: "1 - (x min 0.85)" would parse as "(1 - x) min 0.85"
// and give 0.85 transmission in clear sky (a 15 % loss for no reason).
// Smoothed weather: the engine's rain/overcast can step abruptly (mission
// script, weather clear).  Reading them raw makes the NVG display SNAP to
// a new brightness in one frame (the user report: "as soon as rain stops
// it snaps straight away to a higher brightness").  The shared weather
// foundation EMA-eases them over ~5 s so weather transitions look real.
private _weather = [] call FUNC(getSmoothedWeather);
private _rainS = _weather select 0;
private _overcastS = _weather select 1;

private _cloudLoss = (_overcastS * 0.85) min 0.85;
private _cloudTransmission = 1 - _cloudLoss;
private _moonLight = 0 max ((moonIntensity * _cloudTransmission) - (_rainS * 0.5));

// ─── Twilight glow (NVG-relevant sky light) ──────────────────────────────
// Image intensifiers respond to VISIBLE + near-infrared, and the twilight
// sky glow (scattered sunlight) is huge: ~400 lux at the horizon, ~3 lux
// at civil twilight end (-6 deg), ~0.008 lux at nautical (-12 deg),
// ~0.0008 lux at astronomical (-18 deg).  The moonlight model alone does
// NOT capture this, so NVG would not dim through dawn or brighten through
// dusk.  The sun elevation comes from the verified solar model.
//
// Fit: lux = 10 ^ (2.6 - 0.3 * |elevation|) for the sun below the horizon.
//   elevation  0  -> 10^2.6  = 398 lux
//   elevation -6  -> 10^0.8  =  6.3 lux
//   elevation -12 -> 10^-1.0 =  0.10 lux
//   elevation -18 -> 10^-2.8 = 0.0016 lux (falls below the starlight floor)
// Above the horizon it is daylight and NVG is not used, so the term only
// applies when the sun is at or below the horizon.
private _sunElev = missionNamespace getVariable [QEGVAR(core,currentSunElevation), -90];
if !(_sunElev isEqualType 0) then { _sunElev = -90; };
private _twilightLux = 0;
if (_sunElev <= 0) then {
    _twilightLux = 10 ^ (2.6 - 0.3 * (abs _sunElev));
};

// ─── Starlight floor (SKYBOX COMPATIBILITY HOOK) ────────────────────────
// The 0.001 lux starlight baseline represents the assumed moonless night
// sky.  Skybox mods (brighter starfields, Milky Way, enhanced airglow)
// replace the rendered sky WITHOUT touching our lux model, so their
// brighter sky would otherwise be amplified at the standard-starlight
// gain (over-bright).  Read a live missionNamespace variable so any mod
// can raise the assumed starlight: a brighter sky -> higher lux -> NVG
// gains down -> the brighter sky renders correctly, not blown out.
//   set aee_optics_starlightLux = 0.01;  // a 10x brighter night sky
// Default 0.001 = standard clear-sky starlight.
private _starlightLux = missionNamespace getVariable [QGVAR(starlightLux), 0.001];
if !(_starlightLux isEqualType 0 && _starlightLux > 0) then { _starlightLux = 0.001; };

// ─── Aurora light (issue #112) ─────────────────────────────────────────────
// A bright aurora (Kp 7-9) adds real light to the night sky, peaking at
// ~0.5-1.0 lux in the zenith but sky-integrated over the visible scene
// ~0.01-0.05 lux.  The green 557.7 nm emission sits in the NVG tube's
// peak sensitivity band, so the added lux brightens the image exactly
// like moonlight does: the AGC sees more photons, gain drops, noise
// falls.  Wired here (the shared lux source) means limiting magnitude,
// night classification, and every illuminance consumer inherit it
// automatically.  Scaled by the space-weather aurora intensity (0-1).
private _auroraIntensity = missionNamespace getVariable [QEGVAR(environmental,auroraIntensity), 0];
if !(_auroraIntensity isEqualType 0 && _auroraIntensity > 0) then { _auroraIntensity = 0; };
private _auroraLux = 0.03 * (_auroraIntensity min 1 max 0);

private _ambientLux = _starlightLux + (_moonLight * 0.249) + _twilightLux + _auroraLux;

// ─── Dynamic lux (client only) ───────────────────────────────────────────
// Two sources: (1) IR weapon light from the player, (2) nearby environmental
// light sources (lamps, fires, vehicle lights, flares).  Both feed the AGC
// and photon models — the NVG brightens near artificial light like a real
// tube would.
//
// getLightingAt select 3 (ambientBrightness) is CAMERA-DEPENDENT in Arma 3.
// When facing away from the moon, it reports lower values, which would
// incorrectly darken the NVG image.  We therefore do NOT use it for ambient
// lux — the moonIntensity model handles that.
private _dynamicLux = 0;
private _unit = call CBA_fnc_currentUnit;

// ─── IR weapon light (ACE3 SPIR/DBAL, vanilla IR) ─────────────────────────
// The player's own IR illuminator adds NIR photons to the scene, which the
// tube detects even though the light is invisible to the eye.  We read the
// ENGINE's weapon-light state (isFlashlightOn) — the same action ACE3's
// keybind drives ("GunLightOn") — so ANY mod's IR light works with no
// classnames.  The IR contribution raises lux, which the AGC and photon
// models respond to naturally: brighter image, lower gain, less noise.
// Magnitude: a typical weapon IR illuminator floods the near scene with
// the equivalent of ~0.01 lux of NIR at 5-10 m (1/10 full-moon); this
// brings a starlit scene up to a workable level without overdriving.
private _currentWeapon = currentWeapon _unit;
private _irLux = 0;
if (!isNull _unit && hasInterface && _currentWeapon != "") then {
    if (_unit isFlashlightOn _currentWeapon) then { _irLux = 0.01; };
    if (isLightOn _unit && _irLux == 0) then { _irLux = 0.005; };
    _dynamicLux = _dynamicLux + _irLux;
    missionNamespace setVariable [QGVAR(irLightLux), _irLux];
};

// ─── Environmental light sources (lamps, fires, vehicle lights) ──────────
// Real NVGs amplify ALL photons — they cannot distinguish moonlight from
// a street lamp.  A lamp at 5 m should flood the tube with 1-10 lux,
// triggering AGC gain reduction and brightening the image (not darkening
// it via auto-gating).
//
// Scan nearby objects for light emitters.  Compute illuminance at the
// player position using inverse-square law: E = I / d², where I is the
// luminous intensity (candela) estimated from the light config.  Range
// capped at 100 m — beyond that, even a floodlight contributes < 0.01 lux
// (negligible against moonlight).
//
// Beer-Lambert atmospheric extinction: real rain and fog scatter and absorb
// photons, reducing throw.  Without this term, inverse-square law alone
// over-predicts illumination range.  ITU-R P.1814-1: rain attenuation is
// wavelength-independent from visible to NIR.  Fog attenuation can reach
// 300 dB/km (ITU-R P.1817-1).
//
// Performance: nearestObjects is O(n) in the search radius; 100 m keeps
// the candidate set small.  The scan runs once per tick on the client.
if (!isNull _unit && hasInterface) then {
    // Shared eye state: single source of truth for eye position (cached
    // once per frame; every eye-space system consumes it).
    private _eye = ([_unit] call FUNC(getEyeState)) select 0;

    // ─── Atmospheric extinction coefficient (Beer-Lambert) ────────────
    // γ (per metre) derived from rain and fog intensities.  At the
    // player's position, the atmosphere between them and each light
    // source attenuates the flux: T = e^(-γd).
    //
    // Rain: γ_rain ≈ 15 dB/km at heavy rain (25 mm/h).  The engine
    // `rain` variable (0-1) maps linearly: rain=1 → 50 mm/h (storm),
    // rain=0.5 → 25 mm/h (heavy).  We use the ITU relationship:
    //   γ (dB/km) = k × R^α, with k ≈ 1.075, α ≈ 0.698 (optical)
    // Simplified: rain=1 maps to ~30 dB/km, rain=0.5 to ~10 dB/km.
    //
    // Fog: the engine `fog` value (0-1) approximates visibility.  Dense
    // fog (fog > 0.5, vis < 200 m) can exceed 100 dB/km.  We use a
    // simplified Kim model: γ_fog ≈ 10^(1.7 - 2.0 × vis_km) for vis < 1 km.
    private _rainExtinction = if (_rainS > 0.1) then {
        // Rain attenuation: 0-30 dB/km mapped from rain 0-1
        private _dBkm = _rainS * 30;
        _dBkm / 4343   // convert dB/km to per-metre: γ = dB_km / (10/ln(10) × 1000)
    } else { 0 };

    // Fog: use `fog` variable if available, estimate from overcast + humidity.
    private _fogS = _weather select 2;
    private _fogExtinction = if (_fogS > 0.3) then {
        // Fog attenuation: exponential ramp.  fog=0.5 → ~40 dB/km,
        // fog=1.0 → ~300 dB/km (ITU-R P.1817-1 dense fog limit).
        private _dBkm = 40 * (_fogS / 0.5) ^ 2;
        _dBkm = _dBkm min 300;
        _dBkm / 4343
    } else { 0 };

    private _gamma = _rainExtinction + _fogExtinction;

    private _envLights = nearestObjects [_eye, [], 100];
    {
        private _sim = getText ((configOf _x) >> "simulation");
        private _isLight = false;
        private _lumens = 0;
        if (_sim == "Lamps") then {
            _isLight = true;
            // Street lamp / area light: config brightness is 0..1 mapped
            // to a typical range of 500-5000 lumens.
            private _bright = getNumber ((configOf _x) >> "light" >> "brightness");
            _lumens = 500 + _bright * 4500;
        };
        if (isLightOn _x) then {
            _isLight = true;
            _lumens = 2000;   // vehicle headlights
        };
        if (_x isKindOf "F_40_White" || {_x isKindOf "F_40_Red"
            || {_x isKindOf "F_40_Green" || {_x isKindOf "F_40_Yellow"}}}) then {
            _isLight = true;
            _lumens = 3000;   // flare (very bright)
        };
        if (_isLight && _lumens > 0) then {
            private _dist = _eye distance (getPosASL _x);
            if (_dist > 0.5 && _dist < 100) then {
                // E = lumens / (4π d²) × T, where T = e^(-γd) is the
                // Beer-Lambert transmission factor.  Without T, the model
                // over-predicts illumination in rain/fog.  With T, light
                // sources lose throw in bad weather — matching real NVG
                // behaviour.
                private _transmission = if (_gamma > 0) then { exp (-_gamma * _dist) } else { 1 };
                private _luxContrib = (_lumens / (4 * pi * _dist * _dist)) * _transmission;
                _dynamicLux = _dynamicLux + _luxContrib;
            };
        };
    } forEach _envLights;
};

private _totalLux = _ambientLux + _dynamicLux;

// ─── Night detection ──────────────────────────────────────────────────────
// sunOrMoon: 1 = sun up, 0 = night.  Use it as the authoritative flag.
private _isNight = (sunOrMoon == 0);

missionNamespace setVariable [QGVAR(illuminanceLux), _totalLux];
missionNamespace setVariable [QGVAR(ambientLux), _ambientLux];
missionNamespace setVariable [QGVAR(dynamicLux), _dynamicLux];
missionNamespace setVariable [QGVAR(lightDirection), _lightDir];
missionNamespace setVariable [QGVAR(lightAzimuth), _lightAzimuth];
missionNamespace setVariable [QGVAR(lightElevation), _lightElevation];
missionNamespace setVariable [QGVAR(lightIsNight), _isNight];
missionNamespace setVariable [QGVAR(starsVisibility), _stars];
missionNamespace setVariable [QGVAR(irLightLux), _irLux];

_totalLux
