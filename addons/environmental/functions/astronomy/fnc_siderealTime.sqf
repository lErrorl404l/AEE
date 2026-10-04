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
private _JD = 2451545.0 + 367 * _year - floor(7 * (_year + floor((_month + 9) / 12)) / 4) + floor(275 * _month / 9) + _day - 0.5;

// GMST at 0h UT on the mission date, plus sidereal rate * UT hours.
// Meeus Ch. 12.
private _JD0 = floor(_JD - 0.5) + 0.5;
private _S = _JD0 - 2451545.0;
private _T2 = _S / 36525.0;
// GMST at 0h UT (degrees)
private _GMST0 = 280.46061837 + 360.98564736629 * _S + 0.000387933 * _T2 * _T2;
// Add time of day (mission time)
private _hours = time / 3600;
private _LST = (_GMST0 + 360 * _hours / 24.03) mod 360;
if (_LST < 0) then { _LST = _LST + 360; };

_LST
