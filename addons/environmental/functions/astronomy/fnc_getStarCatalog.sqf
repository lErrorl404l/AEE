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
// The catalogue is static. Build it once and keep it: the environment tick
// calls this every 5 s and rebuilding the 9050 rows each time is wasted work.
private _catalog = missionNamespace getVariable [QGVAR(starCatalogCache), nil];
if (isNil "_catalog") then {
    _catalog = [] call FUNC(starCatalogData);
    missionNamespace setVariable [QGVAR(starCatalogCache), _catalog];
};

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
private _lat = ([] call EFUNC(lib,getWorldLocation)) select 1;
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

// ─── Star brightness coefficient (item 3) ─────────────────────────────────
// Rebuild the Star Light coefficient from the moon phase, the cached ambient
// brightness (getLighting element 1), the cached house count, the engine
// overcast and fog, and the matcher world star scale.  The combined value is a
// 0..1 render-scale multiplier: 1 in a pristine dark sky, lower under moon,
// light pollution, cloud or a harsh world.  Published for the renderers.
private _moonPhase = moonPhase date;
if !(_moonPhase isEqualType 0) then { _moonPhase = 0.5; };

private _ambientBrightness = missionNamespace getVariable [QGVAR(ambientBrightness), 0];
if !(_ambientBrightness isEqualType 0) then { _ambientBrightness = 0; };

private _houseCount = missionNamespace getVariable [QGVAR(houseCount), 0];
if !(_houseCount isEqualType 0) then { _houseCount = 0; };

private _brightnessCoeff = [_moonPhase, _ambientBrightness, _houseCount] call FUNC(starBrightnessCoefficient);
_brightnessCoeff = [_brightnessCoeff, overcast, fog] call FUNC(starWeatherFade);

// Matcher world factor: element 1 of aee_environmental_worldLighting (starScale).
private _worldLighting = missionNamespace getVariable [QGVAR(worldLighting), []];
private _worldStarScale = 1;
if ((_worldLighting isEqualType []) && {(count _worldLighting) > 1}) then {
    _worldStarScale = _worldLighting select 1;
};
if !(_worldStarScale isEqualType 0) then { _worldStarScale = 1; };
_brightnessCoeff = _brightnessCoeff * _worldStarScale;

// Operator display scale (AEE Environmental > Display).
private _operatorScale = GVAR(starBrightnessScale);
if !(_operatorScale isEqualType 0) then { _operatorScale = 1; };
_brightnessCoeff = _brightnessCoeff * _operatorScale;

_brightnessCoeff = ((_brightnessCoeff max 0) min 1);
missionNamespace setVariable [QGVAR(starBrightnessCoefficient), _brightnessCoeff];

// ─── Precession cache (J2000 to the mission date) ─────────────────────────
// Precession depends on the date alone, so precess the whole catalogue once
// per date and keep it. The per-tick loop then applies only the sidereal-time
// and latitude rotation, which keeps the environment tick inside its budget.
private _dateKey = _date select [0, 3];
private _precCache = missionNamespace getVariable [QGVAR(starCatalogPrecessed), []];
private _rows = if (_precCache isEqualTo [] || {(_precCache select 0) isNotEqualTo _dateKey}) then {
    private _built = _catalog apply {
        private _raDeg = _x select 1;
        private _decDeg = _x select 2;
        private _raZeta = _raDeg + _zetaDeg;
        private _cosDec = cos _decDeg;
        private _sinDec = sin _decDeg;
        private _a = _cosDec * sin _raZeta;
        private _b = cos _thetaDeg * _cosDec * cos _raZeta - sin _thetaDeg * _sinDec;
        private _c = sin _thetaDeg * _cosDec * cos _raZeta + cos _thetaDeg * _sinDec;
        private _raPrec = (_a atan2 _b) + _zDeg;
        private _decPrec = asin _c;
        [(_x select 0), sin _raPrec, cos _raPrec, sin _decPrec, cos _decPrec, (_x select 3)]
    };
    missionNamespace setVariable [QGVAR(starCatalogPrecessed), [_dateKey, _built]];
    _built
} else {
    _precCache select 1
};

// ─── Visible-set cache ─────────────────────────────────────────────────────
// The rotation from the precessed equatorial rows to [alt, az] depends only
// on the local sidereal time, the observer latitude, and the magnitude
// filter.  The world latitude is fixed for a mission and the sidereal time
// advances slowly, so the code reuses the built set until one of those inputs
// moves.  0.25 degrees of sidereal time is well under the 0.5-degree moon
// disc, so a cached field is visually identical.  Latitude, limiting
// magnitude, the debug force and the date are compared exactly: a teleport to
// another world, a time jump or a force change recomputes.  The player
// position enters through the latitude the shared geolocation source derives
// from the world.
private _visibleCache = missionNamespace getVariable [QGVAR(starCatalogVisible), []];
private _visible = [];
private _cacheHit = false;
if (_visibleCache isNotEqualTo []) then {
    _visibleCache params ["_cLST", "_cLat", "_cMLim", "_cForce", "_cDate", "_cVisible"];
    // Fold the sidereal-time difference into [-180, 180] so a wrap past 360
    // degrees does not read as a full revolution.
    private _dLST = abs(_LST - _cLST);
    if (_dLST > 180) then { _dLST = 360 - _dLST; };
    if (_dLST <= 0.25
        && (_lat == _cLat)
        && (_mLim == _cMLim)
        && (_starsForce == _cForce)
        && (_dateKey isEqualTo _cDate)) then {
        _visible = _cVisible;
        _cacheHit = true;
    };
};

if (!_cacheHit) then {
    // ─── Compute visible stars ─────────────────────────────────────────────
    private _sinLST = sin _LST;
    private _cosLST = cos _LST;
    private _sinLat = sin _lat;
    private _cosLat = cos _lat;

    {
        // The rows are sorted by magnitude, brightest first, so a star past the
        // limit means every later star is past it too. Stop the scan before the
        // rotation: the tick only pays for the stars it can use.
        if ((_x select 5) > _mLim) exitWith {};

        // Hour angle, from the precomputed right ascension: the sine and cosine
        // of (LST - RA) need no per-star trig.
        private _sinHa = _sinLST * (_x select 2) - _cosLST * (_x select 1);
        private _cosHa = _cosLST * (_x select 2) + _sinLST * (_x select 1);

        // Altitude above horizon (degrees)
        private _altDeg = asin ((_x select 3) * _sinLat + (_x select 4) * _cosLat * _cosHa);

        // Azimuth from north, clockwise.  The Meeus Ch. 13 atan2 form measures
        // from the south, westward; add 180 degrees for the north convention
        // fnc_starDirection documents and consumes.
        if (_altDeg > 0) then {
            private _azDeg = (_sinHa atan2 (_cosHa * _sinLat - ((_x select 3) / (_x select 4)) * _cosLat)) + 180;
            _azDeg = _azDeg mod 360;
            if (_azDeg < 0) then { _azDeg = _azDeg + 360; };
            _visible pushBack [(_x select 0), _altDeg, _azDeg, (_x select 5)];
        };
    } forEach _rows;

    // Sort by altitude, highest first.  The boolean form of sort orders by
    // the first element of each item, so sort a keyed copy that carries the
    // altitude first, then restore the [name, altitude, azimuth, magnitude]
    // shape.  Sorting the raw items would order by the name string instead.
    private _keyed = _visible apply { [(_x select 1), _x] };
    _keyed sort true;
    _visible = _keyed apply { _x select 1 };

    // Keep the inputs beside the set so the next tick can test the cache.
    missionNamespace setVariable [
        QGVAR(starCatalogVisible),
        [_LST, _lat, _mLim, _starsForce, _dateKey, _visible]
    ];
};

missionNamespace setVariable [QGVAR(visibleStars), _visible];

_visible
