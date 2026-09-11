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
private _doy = (_date#1 - 1) * 30 + _date#2;                 // approximate day of year
private _hour = (_date#3) + (time / 3600);                    // local hour fraction
private _lat = getNumber (configFile >> "CfgWorlds" >> worldName >> "latitude");
if (_lat == 0) then { _lat = 40; };

private _decl = 23.45 * sin ((360 / 365) * (_doy + 284));
private _hourAngle = (_hour - 12) * 15;
private _sinElev = (sin _lat) * (sin _decl) + (cos _lat) * (cos _decl) * (cos _hourAngle);

private _radiation = _sinElev max 0;
private _cloudFactor = 1 - (0.75 * _overcast);
(_radiation * _cloudFactor) min 1
