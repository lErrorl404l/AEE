#include "..\..\script_component.hpp"

/*
Solar glare intensity (0.0–1.0) for veiling glare when looking
toward the sun.

Angular difference between player view direction and sun azimuth
determines the glare core — zero at ≥45° offset, maximum when
looking directly at the sun.  Solar elevation shapes the intensity
curve: low sun near the horizon produces stronger veiling glare
through atmospheric scattering.  Overcast proportionally reduces
the effect.

Night / twilight (sunOrMoon ≤ 0) yields zero glare.

Stored in QGVAR(solarGlareIntensity) for consumption by visual
post-process or HUD glare overlay systems.
*/

params [["_unit", objNull, [objNull]]];
if (isNull _unit) then { _unit = call CBA_fnc_currentUnit; };
if (isNull _unit) exitWith {
    missionNamespace setVariable [QGVAR(solarGlareIntensity), 0];
    0
};

// ─── Night check ──────────────────────────────────────────────────────
if (sunOrMoon <= 0) exitWith {
    missionNamespace setVariable [QGVAR(solarGlareIntensity), 0];
    0
};

// ─── Inputs ────────────────────────────────────────────────────────────
// Sun position from the shared illuminance layer (fnc_calculateIlluminance):
// the engine's OWN sun/moon vector via getLighting, converted to azimuth
// and elevation.  This replaces the old dayTime sine approximation — the
// engine's light direction is real data, verified by docker probe (vector
// points FROM the light; elevation is sign-flipped to give sun elevation).
private _sunAzim  = missionNamespace getVariable [QEGVAR(core,lightAzimuth), -1];
private _sunElev  = missionNamespace getVariable [QEGVAR(core,lightElevation), -1];
private _sunValid = (_sunAzim >= 0 && _sunElev >= 0);
if (_sunValid) then {
    // Engine vector points FROM the sun; the sun is the opposite direction,
    // so elevation is negated.  The probe showed vector z ≈ -0.88 → sun
    // elevation ≈ +61.8° (a plausible summer afternoon sun).
    _sunElev = -_sunElev;
} else {
    // Fallback if the illuminance layer has not run yet this tick:
    // the old sine model (dayTime-based), identical shape to the
    // original code so glare never blanks between ticks.
    private _dayFraction = dayTime / 24;
    _sunElev = (sin ((_dayFraction - 0.25) * 360) * 90) max 0;
    _sunAzim = ((_dayFraction - 0.25) * 360) mod 360;
    if (_sunAzim < 0) then { _sunAzim = _sunAzim + 360; };
};
private _viewDir  = getDirVisual _unit;
if (_viewDir != _viewDir) then { _viewDir = getDir _unit; };  // NaN check: fresh AI units have no visual direction
private _overcast = overcast;

if (isNil "_overcast") then { _overcast = 0; };

// ─── Angular difference between view and sun ──────────────────────────
private _angularDiff = abs (_viewDir - _sunAzim);
if (_angularDiff > 180) then { _angularDiff = 360 - _angularDiff; };

// ─── Core glare: angular falloff ──────────────────────────────────────
// Full glare when looking directly at sun (±0°), zero at ≥45° offset
private _coreIntensity = (1 - _angularDiff / 45) max 0;

// ─── Elevation factor ─────────────────────────────────────────────────
// Low sun near horizon = stronger veiling glare (thicker atmospheric path)
// Peaks at elevation ~10°, fades above 50°
private _elevFactor = if (_sunElev < 20) then {
    _sunElev / 20
} else {
    (1 - (_sunElev - 20) / 30) max 0
};

// ─── Combine ──────────────────────────────────────────────────────────
private _intensity = _coreIntensity * _elevFactor;

// Overcast reduction — cloud cover scatters and attenuates direct sunlight
_intensity = _intensity * (1 - _overcast * 0.8);

// Guard
_intensity = _intensity max 0 min 1;

// ─── Store ─────────────────────────────────────────────────────────────
missionNamespace setVariable [QGVAR(solarGlareIntensity), _intensity];

_intensity
