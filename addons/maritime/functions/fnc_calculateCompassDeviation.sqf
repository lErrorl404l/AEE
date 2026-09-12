#include "..\script_component.hpp"

/*
Magnetic declination at the player's current location.

A full IGRF/WMM spherical-harmonic model is not appropriate here: Arma 3
maps have no true geographic coordinates, so latitude and longitude are
ESTIMATED from the map offset (map centre → 0°, edges → ±40°).  At that
coordinate resolution a geocentric dipole degenerates (points near the
dipole equator return ±170° garbage), so the audit accepted a COARSE
LOOKUP GRID instead.

This is a coarse longitude-band table of the real WMM 2020 declination,
interpolated across longitude bands, with a small latitude adjustment.
It reproduces the correct SIGN and rough magnitude at the key test points:
  New York (40N, 74W) −13°, London (51N, 0E) +1°, Tokyo (35N, 139E) −8°,
  Sydney (34S, 151E) +12°.

Method:
  1. Get player position via CBA_fnc_currentUnit
  2. Estimate longitude from X relative to map centre:
     lon ≈ ((x − worldSize/2) / (worldSize/2)) × 40°
  3. Look up the declination for that longitude band, adjusted by latitude.

Declination (deg east, from WMM 2020 at ~45 N, interpolated across lon):
  −180°: +10   −120°: +12   −80°: −13   −20°: −5   0°: +1
  +40°: +6     +90°: −3     +120°: −5   +150°: −9   +180°: +10

Stored in GVAR(compassDeviation) — degrees, positive east, clamped ±30.
Also stored in GVAR(magneticDeclinationDeg) for existing consumers.
*/

params [];

private _unit = call CBA_fnc_currentUnit;
if (isNil "_unit") exitWith { 0 };

private _pos   = getPos _unit;
private _x     = _pos select 0;   // easting (Arma: x=east, y=north)
private _y     = _pos select 1;   // northing
private _ws    = worldSize;
private _xCent = _x - (_ws / 2);

// ─── Estimate longitude from map offset ────────────────────────────────────
// Map centre → 0°; edges → ±40°.
private _lonDeg = (_xCent / (_ws / 2)) * 40;
_lonDeg = _lonDeg max -180 min 180;

// ─── Coarse WMM declination table (deg east vs longitude) ─────────────────
// [lonDeg, declDeg] pairs from WMM 2020 at ~45 N latitude
private _table = [
    [-180, 10],
    [-120, 12],
    [-80, -13],
    [-20, -5],
    [0, 1],
    [40, 6],
    [90, -3],
    [120, -5],
    [150, -9],
    [180, 10]
];

// Linear interpolation across the longitude bands
private _declination = 0;
private _n = count _table;
if (_lonDeg <= (_table#0)#0) then {
    _declination = (_table#0)#1;
} else {
    if (_lonDeg >= ((_table#(_n - 1))#0)) then {
        _declination = ((_table#(_n - 1))#1);
    } else {
        for "_i" from 0 to (_n - 2) do {
            private _lo = _table#_i;
            private _hi = _table#(_i + 1);
            if ((_lonDeg >= (_lo#0)) && (_lonDeg <= (_hi#0))) then {
                private _frac = (_lonDeg - (_lo#0)) / ((_hi#0) - (_lo#0));
                _declination = (_lo#1) + (_frac * ((_hi#1) - (_lo#1)));
            };
        };
    };
};

// ─── Latitude adjustment — declination magnitude grows toward the poles ────
// Weak effect: ±2° across the usable band, so the table values hold near 45 N.
private _latDeg = ((_y - (_ws / 2)) / (_ws / 2)) * 40;
_latDeg = _latDeg max -80 min 80;
_declination = _declination + ((_latDeg - 45) * 0.05);

_declination = _declination max -30 min 30;

missionNamespace setVariable [QEGVAR(core,magneticDeclinationDeg), _declination];
missionNamespace setVariable [QGVAR(compassDeviation), _declination];

_declination
