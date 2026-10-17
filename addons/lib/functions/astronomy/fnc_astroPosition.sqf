#include "..\..\script_component.hpp"
/*
Sun and moon position for an observer (topocentric, airless).

Arguments:
  0: day number, whole days since 2000-01-01 00:00 UT (NUMBER, integer)
  1: UT hours into that day (NUMBER)
  2: geodetic latitude, deg (NUMBER, positive north)
  3: longitude, deg (NUMBER, positive east)

The engine's numbers are 32-bit floats: a Julian Day (~2.46e6) held in one
resolves only to a quarter of a day.  The instant is therefore passed as a
whole day number and UT hours, every angle is formed from a DAILY rate
times the day count (Meeus' century rates / 36525), and the sidereal
rotation takes its fractional day from the UT hours directly.

Return: [lstDeg, eotMin, sunAltDeg, sunAzDeg, sunDecDeg,
         moonAltDeg, moonAzDeg, moonIllumFraction]
  lstDeg      local apparent-ish sidereal time (GMST + longitude), deg
  eotMin      equation of time (apparent - mean solar time), minutes
  *AzDeg      azimuth clockwise from north, deg
  moonIllum   illuminated fraction of the lunar disc, 0..1

Sun: Meeus (1998), Astronomical Algorithms, ch. 25 (low accuracy, ~0.01
deg): mean longitude, mean anomaly, equation of centre, apparent longitude
(nutation and aberration), true obliquity (eq. 22.2, 25.8); GMST eq. 12.4.
Moon: The Astronomical Almanac low-precision formulae (accuracy ~0.3 deg in
longitude, 0.2 deg in latitude), with the horizontal parallax correction
to the topocentric altitude.  Validated against JPL Horizons
(data/astronomy/validation) by tools/tests/test_astronomy.py, which
executes this file.
Public: No
*/

params [["_dn", 0, [0]], ["_utH", 12, [0]], ["_latDeg", 0, [0]], ["_lonDeg", 0, [0]]];

private _fnc_norm = {
    params ["_a"];
    ((_a mod 360) + 360) mod 360
};

// Days and Julian centuries from J2000.0 (2000-01-01 12:00 UT).
private _days = _dn - 0.5 + (_utH / 24);
private _T = _days / 36525;

// ─── Sun (Meeus ch. 25) ───────────────────────────────────────────────────
private _L0 = [280.46646 + 0.98564736016 * _days + 0.0003032 * _T * _T] call _fnc_norm;
private _M = [357.52911 + 0.98560028172 * _days - 0.0001537 * _T * _T] call _fnc_norm;
private _C = (1.914602 - 0.004817 * _T - 0.000014 * _T * _T) * (sin _M)
    + (0.019993 - 0.000101 * _T) * (sin (2 * _M))
    + 0.000289 * (sin (3 * _M));
private _omega = 125.04 - 0.05295376 * _days;
private _lambdaSun = _L0 + _C - 0.00569 - 0.00478 * (sin _omega);
private _eps0 = 23 + (26 + ((21.448 - _T * (46.815 + _T * (0.00059 - 0.001813 * _T))) / 60)) / 60;
private _eps = _eps0 + 0.00256 * (cos _omega);
private _raSun = [((cos _eps) * (sin _lambdaSun)) atan2 (cos _lambdaSun)] call _fnc_norm;
private _decSun = asin ((sin _eps) * (sin _lambdaSun));

// ─── Sidereal time (Meeus eq. 12.4) and equation of time ──────────────────
// 360.98564736629 * days = 360 * frac(days) + 0.98564736629 * days, and
// frac(days) = frac(UT / 24 + 0.5) because the day number is whole.
private _dayFrac = ((_utH / 24) + 0.5) - floor ((_utH / 24) + 0.5);
private _gmst = [280.46061837 + 360 * _dayFrac + 0.98564736629 * _days + 0.000387933 * _T * _T] call _fnc_norm;
private _lst = [_gmst + _lonDeg] call _fnc_norm;
private _eotDeg = [_L0 - 0.0057183 - _raSun + 180] call _fnc_norm;
private _eotMin = 4 * (_eotDeg - 180);

// ─── Horizontal coordinates ───────────────────────────────────────────────
private _fnc_horizontal = {
    params ["_ra", "_dec"];
    private _ha = _lst - _ra;
    private _alt = asin (((sin _latDeg) * (sin _dec)) + ((cos _latDeg) * (cos _dec) * (cos _ha)));
    private _az = [((sin _ha) atan2 (((cos _ha) * (sin _latDeg)) - ((tan _dec) * (cos _latDeg)))) + 180] call _fnc_norm;
    [_alt, _az]
};
private _sun = [_raSun, _decSun] call _fnc_horizontal;

// ─── Moon (Astronomical Almanac, low precision) ───────────────────────────
// Each argument is reduced mod 360 before the trig, so the float32 product
// of a fast daily rate and ~1e4 days keeps ~0.02 deg.
private _a1 = [134.9 + 13.06499247 * _days] call _fnc_norm;
private _a2 = [259.2 - 11.31650595 * _days] call _fnc_norm;
private _a3 = [235.7 + 24.38149843 * _days] call _fnc_norm;
private _a4 = [269.9 + 26.12998494 * _days] call _fnc_norm;
private _a5 = [357.5 + 0.98560027 * _days] call _fnc_norm;
private _a6 = [186.6 + 26.45870089 * _days] call _fnc_norm;
private _lambdaMoon = ([218.32 + 13.17639647 * _days] call _fnc_norm)
    + 6.29 * (sin _a1) - 1.27 * (sin _a2) + 0.66 * (sin _a3)
    + 0.21 * (sin _a4) - 0.19 * (sin _a5) - 0.11 * (sin _a6);
private _betaMoon = 5.13 * (sin ([93.3 + 13.22935058 * _days] call _fnc_norm))
    + 0.28 * (sin ([228.2 + 26.29434278 * _days] call _fnc_norm))
    - 0.28 * (sin ([318.3 + 0.16435811 * _days] call _fnc_norm))
    - 0.17 * (sin ([217.6 - 11.15214784 * _days] call _fnc_norm));
private _parallax = 0.9508
    + 0.0518 * (cos _a1) + 0.0095 * (cos _a2)
    + 0.0078 * (cos _a3) + 0.0028 * (cos _a4);
private _raMoon = [(((sin _lambdaMoon) * (cos _eps)) - ((tan _betaMoon) * (sin _eps))) atan2 (cos _lambdaMoon)] call _fnc_norm;
private _decMoon = asin (((sin _betaMoon) * (cos _eps)) + ((cos _betaMoon) * (sin _eps) * (sin _lambdaMoon)));
private _moon = [_raMoon, _decMoon] call _fnc_horizontal;
// Topocentric altitude: the moon's horizontal parallax lowers it.
private _moonAltTopo = (_moon select 0) - asin ((sin _parallax) * (cos (_moon select 0)));

// Illuminated fraction from the elongation (phase angle ~ 180 - elongation).
private _cosElong = (cos _betaMoon) * (cos (_lambdaMoon - _lambdaSun));
private _illum = (1 - _cosElong) / 2;

[_lst, _eotMin, _sun select 0, _sun select 1, _decSun, _moonAltTopo, _moon select 1, _illum]
