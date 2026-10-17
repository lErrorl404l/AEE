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
// The sun the player SEES is the engine's own light (getLighting, published
// by fnc_calculateIlluminance as the light's azimuth and elevation).  It is
// the sun only while sunOrMoon is 1; in the sun/moon transition the
// astronomical sun (aee_core_currentSunElevation/Azimuth, from
// fnc_calculateSolarRadiation) is used instead.
private _sunAzim = missionNamespace getVariable [QEGVAR(core,lightAzimuth), -1];
private _sunElev = missionNamespace getVariable [QEGVAR(core,lightElevation), -90];
if !(_sunAzim isEqualType 0) then { _sunAzim = -1; };
if (sunOrMoon < 1 || _sunAzim < 0) then {
    _sunAzim = missionNamespace getVariable [QEGVAR(core,currentSunAzimuth), 180];
    _sunElev = missionNamespace getVariable [QEGVAR(core,currentSunElevation), -90];
};
if (_sunElev <= 0) exitWith {
    missionNamespace setVariable [QGVAR(solarGlareIntensity), 0];
    0
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
