#include "..\script_component.hpp"

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
if (isNull _unit) exitWith { 0 };  // no unit on dedicated server

// ─── Night check ──────────────────────────────────────────────────────
if (sunOrMoon <= 0) exitWith {
    missionNamespace setVariable [QGVAR(solarGlareIntensity), 0];
    0
};

// ─── Inputs ────────────────────────────────────────────────────────────
private _sunPos   = getSunPosition;     // [azimuth deg, elevation deg]
private _sunAzim  = _sunPos param [0, 0];
private _sunElev  = _sunPos param [1, 0];
private _viewDir  = getDirVisual _unit;
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
