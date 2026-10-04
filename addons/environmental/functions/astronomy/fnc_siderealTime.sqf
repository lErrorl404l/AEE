#include "..\..\script_component.hpp"

/*
Local sidereal time (degrees).

GMST at 0h UT on the mission date, plus the sidereal rate applied to the
elapsed UT hours (Meeus, Astronomical Algorithms, Ch. 12).  The result is
normalised to [0, 360).

Shared by the star catalogue (fnc_getStarCatalog) and the meteor radiant
projection (fnc_meteorState), so the two cannot drift.

Argument:
  0: Array - mission date [year, month, day]
Returns:
  Number - local sidereal time in degrees.
*/

params [["_date", date, [[]]]];

private _year = _date select 0;
private _month = _date select 1;
private _day = _date select 2;
// Day number to the Julian Day at 0h UT of the mission date (Meeus,
// Astronomical Algorithms, Ch. 7).  The base 1721013.5 is the JD at
// 0h UT; the polynomial supplies the elapsed whole days.  The J2000 base
// (2451545.0) did not give a Julian Day and GMST drifted by ~46 degrees.
private _JD = 1721013.5 + 367 * _year - floor(7 * (_year + floor((_month + 9) / 12)) / 4) + floor(275 * _month / 9) + _day;

// Days since J2000.0 at 0h UT, and the Julian centuries.
private _S = _JD - 2451545.0;
private _T2 = _S / 36525.0;
// GMST at 0h UT (degrees), Meeus Ch. 12.
private _GMST0 = 280.46061837 + 360.98564736629 * _S + 0.000387933 * _T2 * _T2;
// Add the UT fraction of the day at the sidereal rate: 360.98564736629
// degrees per solar day (15.0410686 degrees per solar hour).  The old
// 360/24.03 gave 14.981 degrees per hour, below the solar rate.
private _hours = time / 3600;
private _LST = (_GMST0 + 360.98564736629 * _hours / 24) mod 360;
if (_LST < 0) then { _LST = _LST + 360; };

_LST
