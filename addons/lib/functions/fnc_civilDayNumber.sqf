#include "..\script_component.hpp"
/*
Whole days from 2000-01-01 00:00 UT of a proleptic Gregorian date.

H. Hinnant, "chrono-compatible low-level date algorithms" (days_from_civil):
the era is 400 years, the year of the era, the March-based month index.  Every
intermediate stays below 2^24, so it is exact in the engine's 32-bit floats.

One implementation, shared by the solar-time kernel (fnc_gameClockToUT) and
the geomagnetic model (fnc_calculateCompassDeviation), so the two cannot
disagree on the day count.  The naive day-of-year formula
floor (275 * m / 9) - 2 * floor ((m + 9) / 12) + d - 30 is one day low from
1 March in a leap year, which the geomagnetic model must not inherit.

Arguments:
  0: year (NUMBER)
  1: month, 1..12 (NUMBER)
  2: day of the month (NUMBER)
Return: NUMBER, days since 2000-01-01 (negative before it)
Public: No
*/

params [["_y", 2000, [0]], ["_m", 1, [0]], ["_d", 1, [0]]];

private _yy = _y;
if (_m <= 2) then { _yy = _yy - 1; };
private _era = floor (_yy / 400);
private _yoe = _yy - _era * 400;
private _mp = if (_m > 2) then { _m - 3 } else { _m + 9 };
private _doy = floor ((153 * _mp + 2) / 5) + _d - 1;
private _doe = _yoe * 365 + floor (_yoe / 4) - floor (_yoe / 100) + _doy;
_era * 146097 + _doe - 719468 - 10957
