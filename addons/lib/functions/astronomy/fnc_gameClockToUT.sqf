#include "..\..\script_component.hpp"
/*
UT instant of a game date and clock, as [dayNumber, utHours].

The engine places the sun due south (north) at 12:00 on every map and
centres sunrise and sunset on 12:00 using the world latitude only; BI's
own BIS_fnc_sunriseSunsetTime (functions_f, fn_sunriseSunsetTime.sqf) is
built on exactly that.  The game clock is therefore LOCAL APPARENT SOLAR
TIME, so
  UT = clock - longitude / 15 - equation of time
The equation of time depends on the instant, so it is iterated twice.

The instant is returned as a whole day number since 2000-01-01 00:00 UT
and UT hours into it (0 <= h < 24): the engine's 32-bit floats cannot hold
a Julian Day to better than a quarter of a day.

Arguments:
  0: date [year, month, day, ...] (ARRAY, default date)
  1: clock hours, 0..24 (NUMBER, default dayTime)
  2: longitude, deg east (NUMBER)
Return: [dayNumber, utHours]
Public: No
*/

params [["_date", date, [[]]], ["_clockH", dayTime, [0]], ["_lonDeg", 0, [0]]];
private _y = _date select 0;
private _m = _date select 1;
private _d = _date select 2;

// Whole days from 2000-01-01 (H. Hinnant, "chrono-compatible low-level
// date algorithms", days_from_civil, proleptic Gregorian).  Every
// intermediate stays below 2^24, so it is exact in float32.
private _yy = _y;
if (_m <= 2) then { _yy = _yy - 1; };
private _era = floor (_yy / 400);
private _yoe = _yy - _era * 400;
private _mp = if (_m > 2) then { _m - 3 } else { _m + 9 };
private _doy = floor ((153 * _mp + 2) / 5) + _d - 1;
private _doe = _yoe * 365 + floor (_yoe / 4) - floor (_yoe / 100) + _doy;
private _dn = _era * 146097 + _doe - 719468 - 10957;   // 1970 epoch -> 2000

private _utH = _clockH - (_lonDeg / 15);
for "_i" from 1 to 2 do {
    private _n = _dn;
    private _h = _utH;
    while { _h < 0 } do { _h = _h + 24; _n = _n - 1; };
    while { _h >= 24 } do { _h = _h - 24; _n = _n + 1; };
    private _eot = ([_n, _h, 0, _lonDeg] call FUNC(astroPosition)) select 1;
    _utH = _clockH - (_lonDeg / 15) - (_eot / 60);
};
while { _utH < 0 } do { _utH = _utH + 24; _dn = _dn - 1; };
while { _utH >= 24 } do { _utH = _utH - 24; _dn = _dn + 1; };
[_dn, _utH]
