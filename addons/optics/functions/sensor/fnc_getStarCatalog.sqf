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
private _JD = 2451545.0 + 367 * _year - floor(7 * (_year + floor((_month + 9) / 12)) / 4) + floor(275 * _month / 9) + _day - 0.5;
private _T = (_JD - 2451545.0) / 36525.0;

// Precession angles (degrees per century, Capitaine et al. 2003)
private _zetaA = 2.5976176 + 0.0003980 * _T;  // arcsec per century
private _zA = 2.5976176 + 0.0000060 * _T;
private _thetaA = 20.043109 - 0.0000851 * _T;

// Precession angles to degrees (arcsec / 3600, scaled by the century T).
// SQF trig is degree-native, so no radian conversion is applied.
private _zDeg = _zA * _T / 3600;
private _thetaDeg = _thetaA * _T / 3600;

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

// ─── Compute visible stars ─────────────────────────────────────────────────
private _visible = [];

{
    private _name = _x select 0;
    private _raDeg = _x select 1;
    private _decDeg = _x select 2;
    private _vmag = _x select 3;

    // Skip stars fainter than limiting magnitude
    if (_vmag > _mLim) then { continue; };

    // Apply precession to RA/Dec (both already degrees).
    // Precession (simplified rotation, in degrees - SQF trig is degree-native).
    private _decPrec = asin (sin _decDeg * cos _thetaDeg
        + cos _decDeg * sin _thetaDeg * cos (_raDeg - _zDeg));
    private _raPrec = _raDeg + _zetaA / 3600
        + ((sin _thetaDeg * sin (_raDeg - _zDeg)) atan2 (cos _decDeg * cos _thetaDeg - sin _decDeg * sin _thetaDeg * cos (_raDeg - _zDeg)));

    // Hour angle (degrees)
    private _haDeg = _LST - _raPrec;
    if (_haDeg > 180) then { _haDeg = _haDeg - 360; };
    if (_haDeg < -180) then { _haDeg = _haDeg + 360; };

    // Altitude above horizon (degrees)
    private _altDeg = asin (sin _decPrec * sin _lat
        + cos _decPrec * cos _lat * cos _haDeg);

    // Azimuth (degrees from north, clockwise)
    private _azDeg = (sin _haDeg) atan2 (cos _haDeg * sin _lat - tan _decPrec * cos _lat);
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
