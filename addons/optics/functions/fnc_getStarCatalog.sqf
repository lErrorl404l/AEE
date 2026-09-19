#include "..\script_component.hpp"

/*
Brightest 49 stars with apparent magnitudes and equatorial coordinates.

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
// RA and Dec in degrees (J2000.0).  Top 49 by apparent V magnitude.
// Source: Yale Bright Star Catalogue, Fifth Edition (BSC5).
private _catalog = [
    ["Sirius",          101.2872,  -16.7161, -1.46],
    ["Canopus",         95.9880,  -52.6957, -0.74],
    ["Arcturus",       213.9152,   19.1820, -0.05],
    ["Alpha Centauri",  219.9020,  -60.8340, -0.27],
    ["Vega",           279.2347,   38.7837,  0.03],
    ["Capella",         79.1723,   45.9980,  0.08],
    ["Rigel",           78.6345,   -8.2016,  0.13],
    ["Procyon",        114.8255,    5.2250,  0.34],
    ["Achernar",        24.4289,  -57.2368,  0.46],
    ["Betelgeuse",      88.7930,    7.4071,  0.42],
    ["Hadar",          210.9558,  -60.3730,  0.61],
    ["Altair",         297.6958,    8.8683,  0.76],
    ["Acrux",          186.6497,  -63.0991,  0.76],
    ["Aldebaran",       68.9802,   16.5093,  0.85],
    ["Antares",        247.3519,  -26.4320,  0.96],
    ["Spica",          201.2983,  -11.1613,  0.97],
    ["Pollux",         116.3289,   28.0262,  1.14],
    ["Fomalhaut",      344.4126,  -29.6222,  1.16],
    ["Deneb",          310.3580,   45.2803,  1.25],
    ["Mimosa",         191.9303,  -59.6887,  1.25],
    ["Regulus",        152.0930,   11.9672,  1.35],
    ["Adhara",         104.6562,  -28.9717,  1.50],
    ["Castor",         113.6489,   31.8883,  1.58],
    ["Shaula",         263.4022,  -37.1038,  1.62],
    ["Bellatrix",       81.2828,    6.3497,  1.64],
    ["Elnath",          81.5730,   28.6083,  1.65],
    ["Miaplacidus",    138.2998,  -69.7172,  1.68],
    ["Alnilam",         84.0531,   -1.2019,  1.69],
    ["Alnair",         332.0583,  -46.9611,  1.74],
    ["Alioth",         193.5072,   55.9597,  1.77],
    ["Dubhe",          165.9319,   61.7511,  1.79],
    ["Mirfak",         51.0806,   49.8612,  1.80],
    ["Wezen",         107.0977,  -26.3933,  1.84],
    ["Sargas",         264.3300,  -43.0000,  1.87],
    ["Kaus Australis", 276.0431,  -34.3839,  1.85],
    ["Avior",          125.6287,  -59.5097,  1.86],
    ["Alkaid",         206.8852,   49.3133,  1.86],
    ["Menkalinan",      89.8760,   44.9475,  1.90],
    ["Atria",          252.1663,  -69.0278,  1.92],
    ["Alhena",         99.4280,   16.3992,  1.93],
    ["Peacock",        306.4119,  -56.7351,  1.94],
    ["Mirzam",         95.6750,  -17.9559,  1.98],
    ["Alphard",       141.8968,   -8.6597,  1.98],
    ["Hamal",          32.7936,    23.4624,  2.00],
    ["Polaris",        37.9547,   89.2641,  2.02],
    ["Diphda",         10.9211,  -17.9867,  2.02],
    ["Nunki",           283.8157,  -26.2967,  2.05],
    ["Mizar",          200.9814,   54.9254,  2.27],
    ["Saiph",          86.9390,   -9.6699,  2.09]
];

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

// Convert to radians for calculation
private _zRad = _zA * _T / 3600 * pi / 180;
private _thetaRad = _thetaA * _T / 3600 * pi / 180;

// ─── Player latitude (radians) ────────────────────────────────────────────
// World latitude magnitude from the shared geolocation source (issue
// #179), not a direct CfgWorlds read or the position Y axis: map Y is
// metres, not degrees.  The source normalises the BIS inverted sign and
// returns the magnitude for consumers like this one.
private _lat = ([] call EFUNC(core,getWorldLocation)) select 1;
if (_lat == 0) then { _lat = 40; }; // fallback: temperate default
private _latRad = _lat * pi / 180;

// ─── Local sidereal time (degrees) ────────────────────────────────────────
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

    // Apply precession to RA/Dec
    private _raRad = _raDeg * pi / 180;
    private _decRad = _decDeg * pi / 180;

    // Precession (simplified rotation)
    private _decPrec = asin (sin _decRad * cos _thetaRad
        + cos _decRad * sin _thetaRad * cos (_raRad - _zRad));
    private _raPrec = _raRad + _zetaA / 3600 * pi / 180
        + ((sin _thetaRad * sin (_raRad - _zRad)) atan2 (cos _decRad * cos _thetaRad - sin _decRad * sin _thetaRad * cos (_raRad - _zRad)));

    // Hour angle (degrees)
    private _haDeg = _LST - (_raPrec * 180 / pi);
    if (_haDeg > 180) then { _haDeg = _haDeg - 360; };
    if (_haDeg < -180) then { _haDeg = _haDeg + 360; };
    private _haRad = _haDeg * pi / 180;

    // Altitude above horizon
    private _altRad = asin (sin _decPrec * sin _latRad
        + cos _decPrec * cos _latRad * cos _haRad);
    private _altDeg = _altRad * 180 / pi;

    // Azimuth (degrees from north, clockwise)
    private _azDeg = (sin _haRad) atan2 (cos _haRad * sin _latRad - tan _decPrec * cos _latRad);
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
