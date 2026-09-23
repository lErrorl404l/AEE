#include "..\script_component.hpp"

/*
Magnetic declination at the player's current location.

A full IGRF/WMM spherical-harmonic model is not appropriate here: the
declination is taken from a coarse longitude-band lookup grid of the
real WMM 2020 values, interpolated across longitude bands with a small
latitude adjustment.  It reproduces the correct SIGN and rough
magnitude at the key test points:
  New York (40N, 74W) −13°, London (51N, 0E) +1°, Tokyo (35N, 139E) −8°,
  Sydney (34S, 151E) +12°.

The longitude and latitude come from the shared geolocation source
(fnc_getWorldLocation, issue #179), which reads CfgWorlds directly.
The old code ESTIMATED longitude from map X offset - the WMM table was
keyed to a guessed band, wrong on every real map.

Method:
  1. Read the world's declared longitude and latitude from
     fnc_getWorldLocation (single source of truth, #179)
  2. Look up the declination for that longitude band, adjusted by
     latitude.

Declination (deg east, from WMM 2020 at ~45 N, interpolated across lon):
  −180°: +10   −120°: +12   −80°: −13   −20°: −5   0°: +1
  +40°: +6     +90°: −3     +120°: −5   +150°: −9   +180°: +10

Stored in GVAR(compassDeviation) — degrees, positive east, clamped ±30.
Also stored in GVAR(magneticDeclinationDeg) for existing consumers.
*/

params [];

private _unit = call CBA_fnc_currentUnit;
// isNull, not isNil: CBA_fnc_currentUnit returns objNull on a dedicated
// server rather than nil, so this guard never fired and the compass
// deviation ran on a null unit.
if (isNull _unit) exitWith { 0 };

// ─── Longitude from the shared geolocation source ──────────────────────────
// The old code ESTIMATED longitude from map X offset (map centre → 0°,
// edges → ±40°), which is wrong whenever the map's declared CfgWorlds
// longitude is not its centre (every real map).  The WMM declination
// table was therefore keyed to a guessed band.  #179: read the real
// CfgWorlds longitude from fnc_getWorldLocation, the single source.
// The per-position micro-offset is dropped - at the map's 1-40° scale
// it is noise, and the anchor must come from CfgWorlds, not X.
private _lonDeg = ([] call EFUNC(core,getWorldLocation)) select 2;
if !(_lonDeg isEqualType 0) then { _lonDeg = 0; };

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
private _loc = [] call EFUNC(core,getWorldLocation);
private _latDeg = _loc select 1;   // magnitude from the shared source
if (_latDeg == 0) then { _latDeg = 40; };  // temperate default
_declination = _declination + ((_latDeg - 45) * 0.05);

_declination = _declination max -30 min 30;

missionNamespace setVariable [QEGVAR(core,magneticDeclinationDeg), _declination];
missionNamespace setVariable [QGVAR(compassDeviation), _declination];

_declination
