#include "..\script_component.hpp"

/*
Surface ocean current model (issue #28): the vector sum of a wind-driven
current and a tidal current, with the Ekman transport and depth as
diagnostics.

The engine has no ocean current, so AEE derives one from state it already
computes: the wind vector (aee_core_currentWind), the harmonic tide height
(aee_core_currentTideOffset_m) and the map latitude (getWorldLocation).

  V_wind  = k * U10, deflected theta to the right of the wind (NH)
  V_tidal = |eta| * sqrt(g / H), along the flood axis, reversed on the ebb
  V_total = V_wind + V_tidal             (vector sum, m s^-1)

The wind-driven current is the empirical 1-3% of the 10 m wind (Wu 1975;
Stewart 2008), here k = oceanWindCurrentFraction (default 3%).  The
deflection is theta = oceanDeflectionDeg to the right of the wind in the
northern hemisphere and to the left in the southern (Ekman 1905), default 30
degrees.  The Ekman transport M, Ekman depth D_e and Ekman surface speed come
from the pure kernel FUNC(ekmanTransport).

The tidal current is the shallow-water progressive-wave result
u = eta * sqrt(g / H), from the pure kernel FUNC(tidalCurrentSpeed).  The
flood axis is a scenario parameter (oceanTidalFloodBearing) because the engine
exposes no bathymetry or channel orientation.  Spring and neap scaling is
carried by eta itself: the harmonic tide model already beats M2 against S2, so
the current rises and falls with the tide range and no second tide model is
introduced.

Publishes:
  aee_maritime_oceanCurrent        - [east, north] current vector, m s^-1
  aee_maritime_oceanCurrentSpeed   - current speed, m s^-1
  aee_maritime_oceanCurrentDir     - current azimuth, degrees from north
  aee_maritime_windCurrentSpeed    - wind-driven part, m s^-1
  aee_maritime_tidalCurrentSpeed   - tidal part, m s^-1
  aee_maritime_ekmanTransport_m2s  - Ekman volume transport, m^2 s^-1
  aee_maritime_ekmanDepth_m        - Ekman e-folding depth, m

Input:  none
Output: the current vector [east, north], m s^-1
*/

private _enabled = missionNamespace getVariable [QGVAR(oceanCurrentEnabled), true];
if !(_enabled isEqualType true) then { _enabled = true; };
if (!_enabled) exitWith { [0, 0] };

// ─── Wind-driven current ──────────────────────────────────────────────────
// currentWind is a velocity vector; the wind azimuth is the direction the
// air moves toward, so x atan2 y is the same convention fnc_updateWind uses.
private _wind = missionNamespace getVariable [QEGVAR(core,currentWind), [0, 0]];
if !(_wind isEqualType []) then { _wind = [0, 0]; };
private _U10 = vectorMagnitude _wind;

private _fraction = missionNamespace getVariable [QGVAR(oceanWindCurrentFraction), 0.03];
if !(_fraction isEqualType 0) then { _fraction = 0.03; };
private _windSpeed = _fraction * _U10;

private _lat = ([] call EFUNC(lib,getWorldLocation)) select 0;
if !(_lat isEqualType 0) then { _lat = 0; };

private _deflection = missionNamespace getVariable [QGVAR(oceanDeflectionDeg), 30];
if !(_deflection isEqualType 0) then { _deflection = 30; };
// Right of the wind in the north, left in the south.
private _sign = [-1, 1] select (_lat >= 0);

private _windAz = (_wind select 0) atan2 (_wind select 1);
private _windAzCur = _windAz + (_sign * _deflection);
private _windCur = [_windSpeed * sin _windAzCur, _windSpeed * cos _windAzCur];

// ─── Ekman transport and depth (diagnostics) ──────────────────────────────
private _ekman = [_U10, _lat] call FUNC(ekmanTransport);
_ekman params [["_transport", 0], ["_ekmanDepth", 0], ["_ekmanSurface", 0]];

// ─── Tidal current ────────────────────────────────────────────────────────
private _tide = missionNamespace getVariable [QEGVAR(core,currentTideOffset_m), 0];
if !(_tide isEqualType 0) then { _tide = 0; };
private _depth = missionNamespace getVariable [QGVAR(oceanChannelDepth_m), 30];
if !(_depth isEqualType 0) then { _depth = 30; };
private _tidalSpeed = [_tide, _depth] call FUNC(tidalCurrentSpeed);

// Flood runs up the channel; the ebb reverses it.  The harmonic model
// publishes the state in the tide description.
private _tideDesc = missionNamespace getVariable [QEGVAR(core,currentTideDescription), ""];
if !(_tideDesc isEqualType "") then { _tideDesc = ""; };
private _ebb = _tideDesc find "Falling" >= 0;

private _floodBearing = missionNamespace getVariable [QGVAR(oceanTidalFloodBearing), 0];
if !(_floodBearing isEqualType 0) then { _floodBearing = 0; };
private _tidalBearing = _floodBearing + ([0, 180] select _ebb);
private _tidalCur = [_tidalSpeed * sin _tidalBearing, _tidalSpeed * cos _tidalBearing];

// ─── Total current ────────────────────────────────────────────────────────
private _total = [(_windCur select 0) + (_tidalCur select 0), (_windCur select 1) + (_tidalCur select 1)];
private _speed = vectorMagnitude _total;
private _dir = (_total select 0) atan2 (_total select 1);
if (_speed == 0) then { _dir = 0; };
if (_dir < 0) then { _dir = _dir + 360; };

missionNamespace setVariable [QGVAR(oceanCurrent), _total];
missionNamespace setVariable [QGVAR(oceanCurrentSpeed), _speed];
missionNamespace setVariable [QGVAR(oceanCurrentDir), _dir];
missionNamespace setVariable [QGVAR(windCurrentSpeed), _windSpeed];
missionNamespace setVariable [QGVAR(tidalCurrentSpeed), _tidalSpeed];
missionNamespace setVariable [QGVAR(ekmanTransport_m2s), _transport];
missionNamespace setVariable [QGVAR(ekmanDepth_m), _ekmanDepth];

_total
