#include "..\..\script_component.hpp"
/*
Fog from the air cooling below its dew point.

The air's water-vapour pressure is held at the day's value (published by
fnc_updateHumidity); when the temperature falls below the dew point the
excess vapour condenses.  The liquid water content is
  LWC = rho_v(e, T) - rho_vs(T),   rho = 100 e / (R_v T_K) * 1000  g/m3,
capped at 0.5 g/m3, the top of the observed fog range (Gultepe et al. 2007,
Pure Appl. Geophys. 164:1121).  Its extinction is Kunkel (1984), the cloud
water relation of NOAA's operational post-processor (UPP CALVIS):
  sigma = 144.7 * LWC^0.88   per km.
The fog clears as the sun warms the air above the dew point; nothing else
burns it off.

The engine fog is the renderer's only distance-dependent extinction (it
fades objects as exp(-sigma r), Koschmieder's law), so it carries the WHOLE
atmospheric extinction: fog droplets, the clear-air haze (fnc_calculateHaze,
published one tick earlier) and rain (Atlas 1954, 0.21 R^0.74 per km, R in
mm/h).  Aerial perspective is distance-dependent, so no screen-wide
desaturation stands in for it.  The engine fog is global, so the SERVER sets
it.  The engine value is the 0..1 density fog = sigma / 10 per km; the
engine's own fog-to-visibility curve is not documented and needs a rendered
calibration.  The setting aee_atmos_maxFogDensity caps it.

Publishes: aee_core_currentFogDensity (engine 0..1), aee_core_currentFogLWC
(g/m3), aee_core_currentFogExtinction (fog droplets, per km),
aee_core_currentExtinction (fog + haze + rain, per km).
*/
if (!isServer) exitWith {};

private _T = missionNamespace getVariable [QEGVAR(core,currentTemperature), 15];
if !(_T isEqualType 0) then { _T = 15; };
private _e = missionNamespace getVariable [QEGVAR(core,currentVapourPressure), 0];
if !(_e isEqualType 0) then { _e = 0; };

private _tK = _T + KELVIN_OFFSET;
private _ew = 6.112 * exp (17.62 * _T / (243.12 + _T));
private _rhoV = 100 * _e / (R_WATER_VAPOUR * _tK) * 1000;     // g/m3
private _rhoVs = 100 * _ew / (R_WATER_VAPOUR * _tK) * 1000;   // g/m3
private _lwc = ((_rhoV - _rhoVs) max 0) min 0.5;
private _sigma = if (_lwc > 0) then { 144.7 * (_lwc ^ 0.88) } else { 0 };

private _maxFogDensity = missionNamespace getVariable [QGVAR(maxFogDensity), 0.8];
if !(_maxFogDensity isEqualType 0) then { _maxFogDensity = 0.8; };
private _haze = missionNamespace getVariable [QEGVAR(core,currentHaze), 0];
if !(_haze isEqualType 0) then { _haze = 0; };
private _rainMMH = (rain * ENGINE_RAIN_FULL_MMH) max 0;
private _sigmaRain = if (_rainMMH > 0) then { 0.21 * (_rainMMH ^ 0.74) } else { 0 };
private _sigmaTotal = _sigma + (_haze max 0) + _sigmaRain;
private _fogDensity = ((_sigmaTotal / 10) max 0) min (_maxFogDensity min 1);

missionNamespace setVariable [QEGVAR(core,currentFogLWC), _lwc];
missionNamespace setVariable [QEGVAR(core,currentFogExtinction), _sigma];
missionNamespace setVariable [QEGVAR(core,currentExtinction), _sigmaTotal];
missionNamespace setVariable [QEGVAR(core,currentFogDensity), _fogDensity];
0 setFog [_fogDensity, 0.5, 0];

// ─── Engine fog forecast (trend) ─────────────────────────────────────────
private _forecast = fogForecast;
if (_forecast isEqualType [] && {count _forecast >= 3}) then {
    missionNamespace setVariable [QEGVAR(core,fogForecast), _forecast];
} else {
    missionNamespace setVariable [QEGVAR(core,fogForecast), [_fogDensity, 0.5, 0]];
};
_fogDensity
