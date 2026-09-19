#include "..\script_component.hpp"

/*
Solar radiation factor in [0, 1] for the current date, time and world.

A solar-elevation model: declination from day of year, hour angle from
local time, elevation from latitude, radiation = max(0, sin(elevation)).
Overcast reduces transmission (25% at full overcast). The result drives
the diurnal temperature curve and UV.

Arguments:
  0: overcast (Number 0..1, engine value)

Return Value:
  Number 0..1
*/

params [["_overcast", 0, [0]]];

private _date = date;
private _year = _date#0; private _month = _date#1; private _day = _date#2;
private _doy = floor (275 * _month / 9) - (2 * floor ((_month + 9) / 12)) + _day - 30; // Bauleova formula
if (_month > 2 && (_year mod 4 == 0 && (_year mod 100 != 0 || _year mod 400 == 0))) then { _doy = _doy + 1; }; // leap year
// Current in-game hour from dayTime (0..24) — the canonical source.  The
// old date#3 + time/3600 combined the mission START hour with elapsed
// time, which drifts and misbehaves when the mission clock is skipped or
// the mission runs long.  dayTime is the live clock.
private _hour = dayTime;
// Latitude magnitude from the shared source (fnc_getWorldLocation,
// issue #179).  The magnitude drives max sun elevation; the declination
// term carries the season, so the sign never affects the curve.  The
// source normalises the BIS inverted sign to the true geographic
// convention, and the #123 RC2b Scottish Highlands case (CfgWorlds
// latitude = -56.702) resolves to magnitude 56.7 N correctly.
private _loc = [] call FUNC(getWorldLocation);
private _lat = _loc select 1;  // magnitude
if (_lat == 0) then { _lat = 40; };

private _decl = 23.45 * sin ((360 / 365) * (_doy + 284));
// Hour angle with longitude correction (issue #179).  The old formula
// (_hour - 12) * 15 pinned solar noon to 12:00 game time on every map;
// a map off the prime meridian peaks earlier or later by its real
// longitude.  Solar noon offset from the UTM zone central meridian:
//   hourAngle = (hour - 12) * 15 + (lon - zoneMeridian)
// in degrees, where the zone meridian is the standard
//   zoneMeridian = (zone - 1) * 6 - 180 + 3
// (Stratis: zone 35 -> meridian 27 E, lon 16.48 -> noon ~12:42;
//  oski_corran: zone 30 -> meridian -3, lon -5.22 -> noon ~12:09).
private _lon = _loc select 2;
private _zone = _loc select 3;
private _zoneMeridian = if (_zone > 0) then { (_zone - 1) * 6 - 177 } else { 0 };
private _hourAngle = (_hour - 12) * 15 + (_lon - _zoneMeridian);
private _sinElev = (sin _lat) * (sin _decl) + (cos _lat) * (cos _decl) * (cos _hourAngle);

private _radiation = _sinElev max 0;
private _cloudFactor = 1 - (0.75 * _overcast);
private _result = (_radiation * _cloudFactor) min 1;

// ─── Solar flux in W/m2 (issue #124 audit) ───────────────────────────────
// The 0..1 factor is sin(elevation) x cloud attenuation.  The real flux
// is that factor scaled by the clear-sky hemispherical irradiance:
//   G = G0 * factor,  G0 = 1000 W/m2
// ASTM G173-23 gives 1001.92 W/m2 clear-sky hemispherical at AM1.5, so
// 1000 is the engineering standard value.  This is the quantity every
// thermal surface solve needs (q_solar = alpha * G), and the OLD code
// wrongly multiplied the 0..1 factor by a magic 15 and treated the
// result as degrees Celsius - 196x too big at noon (audit 2026-09-19).
missionNamespace setVariable [QEGVAR(core,currentSolarFlux), _result * 1000];
missionNamespace setVariable [QEGVAR(core,currentSolarRadiation), _result];

// Sun elevation in degrees (asin returns degrees in Arma).  Exposed for the
// NVG twilight model: the twilight sky glow is a function of how far the
// sun is BELOW the horizon, which the radiation value (max 0) cannot give.
private _sunElevation = asin (_sinElev max -1 min 1);
missionNamespace setVariable [QEGVAR(core,currentSunElevation), _sunElevation];

// Store for soil moisture, UV and other consumers
missionNamespace setVariable [QEGVAR(core,currentSolarRadiation), _result];

_result
