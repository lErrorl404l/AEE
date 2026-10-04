#include "..\..\script_component.hpp"

/*
Full star catalogue (V <= 7.0) with apparent magnitudes and equatorial
coordinates, loaded from the generated FUNC(starCatalogData).

Catalog data: Yale Bright Star Catalogue (BSC5), Fifth Edition.
Positions are J2000.0 epoch.  Precession to current date is handled
by the visibility function.

Input: [_posASL] - player position (for latitude/longitude).
Input: [_date] - mission date array [year, month, day].

Returns: array of visible stars, each [name, altitude, azimuth, magnitude].
Stars below the horizon (altitude < 0) or fainter than the limiting
magnitude are excluded.

Stores: QGVAR(visibleStars) as array.
*/

params [
    ["_posASL", [0, 0, 0], [[]]],
    ["_date", date, [[]]]
];

// ─── Star catalog: [name, RA_deg, Dec_deg, Vmag] ─────────────────────────
// Full Yale Bright Star Catalogue (V <= 7.0), generated from
// data/astronomy/sources/catalog.dat by tools/validation/gen_star_catalog.py.
// RA and Dec are J2000.0 degrees; entries are sorted by magnitude.
private _catalog = [] call FUNC(starCatalogData);

// ─── Precession correction (J2000 to current date) ────────────────────────
// Simple precession in RA/Dec.  Good to ~1 arcmin over a century.
// T = centuries from J2000.0 (2000-01-01 12:00 TT).
private _year = _date#0;
private _month = _date#1;
private _day = _date#2;
// Day number to the Julian Day at 0h UT (Meeus, Astronomical Algorithms,
// Ch. 7).  The base 1721013.5 is the JD at 0h UT.  The old J2000 base
// (2451545.0) gave _T about 20.25 centuries at 2025, not 0.25, so the
// precession angle was over-applied by about 0.11 degrees.
private _JD = 1721013.5 + 367 * _year - floor(7 * (_year + floor((_month + 9) / 12)) / 4) + floor(275 * _month / 9) + _day;
private _T = (_JD - 2451545.0) / 36525.0;

// Precession angles (IAU 1976, Lieske et al. 1977; Meeus, Astronomical
// Algorithms, Ch. 21), arcseconds.  T is Julian centuries from J2000.0.
// The previous constants were annual-arcsec values applied per century,
// so every angle was about 100 times too small.
private _zetaArc = 2306.2181 * _T + 0.30188 * _T * _T + 0.017998 * _T * _T * _T;
private _zArc = 2306.2181 * _T + 1.09468 * _T * _T + 0.018203 * _T * _T * _T;
private _thetaArc = 2004.3109 * _T - 0.42665 * _T * _T - 0.041833 * _T * _T * _T;

// Degrees.  SQF trig is degree-native, so no radian conversion is applied.
private _zetaDeg = _zetaArc / 3600;
private _zDeg = _zArc / 3600;
private _thetaDeg = _thetaArc / 3600;

// ─── Player latitude (degrees) ────────────────────────────────────────────
// World latitude magnitude from the shared geolocation source (issue
// #179), not a direct CfgWorlds read or the position Y axis: map Y is
// metres, not degrees.  The source normalises the BIS inverted sign and
// returns the magnitude for consumers like this one.
private _lat = ([] call EFUNC(core,getWorldLocation)) select 1;
if (_lat == 0) then { _lat = 40; }; // fallback: temperate default

// ─── Local sidereal time (degrees) ────────────────────────────────────────
// Shared kernel (Meeus Ch. 12), so the star field and the meteor radiants
// read one sidereal-time source.
private _LST = [_date] call FUNC(siderealTime);

// ─── Get limiting magnitude ───────────────────────────────────────────────
private _mLim = missionNamespace getVariable [QGVAR(limitingMagnitude), 6.5];
// Debug force, set on missionNamespace: aee_environmental_starsForce raises
// the magnitude ceiling used for the visible set, so the immediate-mode faint
// layer has catalogue rows to draw.  It changes the debug filter only, not the
// NELM model.
private _starsForce = missionNamespace getVariable [QGVAR(starsForce), 0];
if (_starsForce isEqualType 0) then {
    if (_starsForce > 0) then { _mLim = _starsForce; };
};

// ─── Compute visible stars ─────────────────────────────────────────────────
private _visible = [];

{
    private _name = _x select 0;
    private _raDeg = _x select 1;
    private _decDeg = _x select 2;
    private _vmag = _x select 3;

    // Skip stars fainter than limiting magnitude
    if (_vmag > _mLim) then { continue; };

    // Apply precession to RA/Dec (both already degrees) with the standard
    // equatorial rotation (Meeus Ch. 21, eq. 21.4).
    private _raZeta = _raDeg + _zetaDeg;
    private _cosDec = cos _decDeg;
    private _sinDec = sin _decDeg;
    private _a = _cosDec * sin _raZeta;
    private _b = cos _thetaDeg * _cosDec * cos _raZeta - sin _thetaDeg * _sinDec;
    private _c = sin _thetaDeg * _cosDec * cos _raZeta + cos _thetaDeg * _sinDec;
    private _raPrec = (_a atan2 _b) + _zDeg;
    private _decPrec = asin _c;

    // Hour angle (degrees)
    private _haDeg = _LST - _raPrec;
    if (_haDeg > 180) then { _haDeg = _haDeg - 360; };
    if (_haDeg < -180) then { _haDeg = _haDeg + 360; };

    // Altitude above horizon (degrees)
    private _altDeg = asin (sin _decPrec * sin _lat
        + cos _decPrec * cos _lat * cos _haDeg);

    // Azimuth from north, clockwise.  The Meeus Ch. 13 atan2 form measures
    // from the south, westward; add 180 degrees for the north convention
    // fnc_starDirection documents and consumes.
    private _azDeg = ((sin _haDeg) atan2 (cos _haDeg * sin _lat - tan _decPrec * cos _lat)) + 180;
    _azDeg = _azDeg mod 360;
    if (_azDeg < 0) then { _azDeg = _azDeg + 360; };

    // Only include stars above the horizon
    if (_altDeg > 0) then {
        _visible pushBack [_name, _altDeg, _azDeg, _vmag];
    };
} forEach _catalog;

// Sort by altitude, highest first.  The boolean form of sort orders by
// the first element of each item, so sort a keyed copy that carries the
// altitude first, then restore the [name, altitude, azimuth, magnitude]
// shape.  Sorting the raw items would order by the name string instead.
private _keyed = _visible apply { [(_x select 1), _x] };
_keyed sort true;
_visible = _keyed apply { _x select 1 };

missionNamespace setVariable [QGVAR(visibleStars), _visible];

_visible
