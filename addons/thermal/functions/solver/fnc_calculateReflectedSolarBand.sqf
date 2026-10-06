#include "..\..\script_component.hpp"
/*
Reflected-solar band radiance (aee-thermal-realism T4).

A daytime MWIR scene is driven partly by reflected sunlight.  This pure kernel
returns that reflected radiance for an opaque Lambertian surface.  It is zero
for the LWIR band, because the solar contribution over 8-14 um is negligible,
and it is zero when the sun is at or below the horizon.

The solar band radiance comes from the Planck function at the adopted solar
effective temperature T_sun = 5772 K.  The top-of-atmosphere band irradiance
is

    E_sunBand = pi * B_band(T_sun) * (R_sun / AU)^2

with R_sun = 6.957e8 m and AU = 1.495978707e11 m.  The reflected radiance for
an opaque Lambertian surface is

    W_solar = (1 - eps) * E_sunBand * max(sin(elevDeg), 0) / pi

The formula is DERIVED from the Planck function and the solar constant.  No
solar spectral irradiance table is used.

The elevation is an argument.  The caller computes it with
fnc_solarElevation.sqf; this kernel holds no second solar model.

Arguments:
  0: bandToken (STRING, "lwir" or "mwir", default "lwir")
  1: eps (NUMBER, surface emissivity, clamped 0..1)
  2: solarElevationDeg (NUMBER, degrees above the horizon)

Return Value: NUMBER, reflected-solar band radiance W/m2/sr.  Zero for LWIR
and zero when the sun is at or below the horizon.
Example: ["mwir", 0.92, 45] call aee_thermal_fnc_calculateReflectedSolarBand
Public: No
*/
params [
    ["_bandToken", "lwir", [""]],
    ["_eps", 0.95, [0]],
    ["_solarElevationDeg", -90, [0]]
];

if !(_eps isEqualType 0) exitWith { 0 };
if !(_solarElevationDeg isEqualType 0) exitWith { 0 };
if !(finite _eps) exitWith { 0 };
if !(finite _solarElevationDeg) exitWith { 0 };
_eps = (_eps max 0) min 1;

// LWIR: the solar contribution in 8-14 um is negligible.
if ((toLower _bandToken) != "mwir") exitWith { 0 };

// SQF sin takes degrees.  At or below the horizon there is no direct beam.
private _sinElev = sin _solarElevationDeg;
if (_sinElev <= 0) exitWith { 0 };

private _bandEdges = [_bandToken] call FUNC(resolveThermalBand);
private _lambda1M = _bandEdges select 0;
private _lambda2M = _bandEdges select 1;

// Top-of-atmosphere band irradiance from the Planck function at T_sun.
private _tSunK = 5772;
private _bSun = [_tSunK, _lambda1M, _lambda2M] call FUNC(planckBandRadiance);
private _rSunM = 6.957e8;
private _auM = 1.495978707e11;
private _eSunBand = pi * _bSun * (_rSunM / _auM) ^ 2;

// Reflected radiance for an opaque Lambertian surface.  The (1 - eps) factor
// is the surface reflectance by Kirchhoff's law.
(1 - _eps) * _eSunBand * _sinElev / pi
