#include "..\..\script_component.hpp"
/*
Sun and moon position, and the global horizontal solar irradiance.

Position: aee_lib_fnc_astroPosition (Meeus ch. 25 sun, Astronomical
Almanac moon; validated against JPL Horizons) for the world's geographic
location at the mission date and clock.  The clock is local apparent solar
time, as the engine renders it (sun due south/north at 12:00; BI's
BIS_fnc_sunriseSunsetTime), converted to UT by aee_lib_fnc_gameClockToUT.

Irradiance, W/m2:
  clear sky   Haurwitz (1945):  G_clear = 1098 cos(z) exp(-0.057 / cos(z))
  cloud       Kasten & Czeplak (1980, Solar Energy 24:177):
              G = G_clear * (1 - 0.75 * N^3.4),  N the cloud cover 0..1
(the engine overcast is taken as the cloud fraction N).

Arguments:
  0: overcast (Number 0..1, engine value)
Return: the irradiance as a fraction of 1000 W/m2 (0..~1.1)
Publishes: aee_core_currentSolarFlux (W/m2), currentSolarRadiation (0..1),
  currentSunElevation/Azimuth, currentMoonElevation/Azimuth,
  currentMoonIllumination, currentLocalSiderealTime, currentUTInstant
  ([days since 2000-01-01, UT hours]).
*/

params [["_overcast", 0, [0]]];

private _loc = [] call EFUNC(lib,getWorldLocation);
private _lat = _loc select 0;   // signed, positive north
private _lon = _loc select 2;

private _ut = [date, dayTime, _lon] call EFUNC(lib,gameClockToUT);
private _astro = [_ut select 0, _ut select 1, _lat, _lon] call EFUNC(lib,astroPosition);
_astro params ["_lst", "_eot", "_sunElevation", "_azimuth", "_decSun", "_moonElevation", "_moonAzimuth", "_moonIllum"];

// ─── Irradiance ───────────────────────────────────────────────────────────
private _cosZ = sin (_sunElevation max 0);
private _gClear = 0;
if (_cosZ > 0.001) then {
    _gClear = 1098 * _cosZ * exp (-0.057 / _cosZ);
};
private _n = (_overcast max 0) min 1;
private _flux = _gClear * (1 - 0.75 * (_n ^ 3.4));
private _result = _flux / 1000;

missionNamespace setVariable [QEGVAR(core,currentSolarFlux), _flux];
missionNamespace setVariable [QEGVAR(core,currentSolarRadiation), _result];
missionNamespace setVariable [QEGVAR(core,currentSunElevation), _sunElevation];
missionNamespace setVariable [QEGVAR(core,currentSunAzimuth), _azimuth];
missionNamespace setVariable [QEGVAR(core,currentSunDeclination), _decSun];
missionNamespace setVariable [QEGVAR(core,currentMoonElevation), _moonElevation];
missionNamespace setVariable [QEGVAR(core,currentMoonAzimuth), _moonAzimuth];
missionNamespace setVariable [QEGVAR(core,currentMoonIllumination), _moonIllum];
missionNamespace setVariable [QEGVAR(core,currentLocalSiderealTime), _lst];
missionNamespace setVariable [QEGVAR(core,currentUTInstant), _ut];

_result
