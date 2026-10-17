#include "..\..\script_component.hpp"
/*
 * aee_lib_fnc_gnssSatellites
 *
 * GPS satellites above the mask angle for an observer and an instant.
 * Pure: reads only the generated constellation table (fnc_gnssTables).
 *
 * The constellation is the GPS SPS Performance Standard (5th ed., 2020)
 * slot table, fully expanded (30 locations), on circular orbits
 * (a 26559.8 km, i 55 deg) with the published nodal regression and the
 * mean motion that keeps the groundtracks stationary.  The inertial
 * position is rotated into the Earth frame by the Greenwich hour angle
 * (100.765 deg at the 2016-12-31 23:59:43 UTC epoch plus the sidereal
 * rate).  The model reproduces every published groundtrack crossing
 * (tools/gen_gnss.py).
 *
 * Arguments:
 *   0: day number, whole days since 2000-01-01 (NUMBER)
 *   1: UT hours (NUMBER)
 *   2: geodetic latitude, deg (NUMBER)
 *   3: longitude, deg (NUMBER)
 *   4: mask angle, deg (NUMBER, default: the table's 5 deg)
 *   5: observer height above the WGS84 ellipsoid, km (NUMBER, default 0:
 *      a ground unit).  A receiver on a hill or in the air sees a wider sky,
 *      so its height enters the observer's ECEF position.
 *
 * Return: ARRAY of [east, north, up] unit line-of-sight vectors, one per
 *         satellite above the mask.
 */
params [["_dn", 0, [0]], ["_utH", 0, [0]], ["_lat", 0, [0]], ["_lon", 0, [0]], ["_mask", -1, [0]], ["_altKm", 0, [0]]];
private _t = call FUNC(gnssTables);
if (_mask < 0) then { _mask = _t get "maskDeg"; };

// Days since the constellation epoch, kept small for float32.
private _days = (_dn - (_t get "epochDay")) + ((_utH - (_t get "epochHours")) / 24);
private _nodeRate = _t get "nodeRate";
private _inc = _t get "incDeg";
private _a = _t get "aKm";
private _fnc_norm = { params ["_x"]; ((_x mod 360) + 360) mod 360 };
// Earth rotation angle: whole days contribute 0.98564736629 deg each, the
// fraction 360 deg per day, so no large product is formed.
private _theta = [(_t get "gha0") + 0.98564736629 * _days + 360 * (_days - floor _days)] call _fnc_norm;

// Observer (WGS84) at the receiver height.
private _e2 = (1 / 298.257223563) * (2 - (1 / 298.257223563));
private _nr = 6378.137 / sqrt (1 - _e2 * (sin _lat) ^ 2);
private _px = (_nr + _altKm) * (cos _lat) * (cos _lon);
private _py = (_nr + _altKm) * (cos _lat) * (sin _lon);
private _pz = (_nr * (1 - _e2) + _altKm) * (sin _lat);

// Argument-of-latitude advance n * days with n = 2 (earthRate - nodeRate),
// reduced mod 360 before the factor 2 so float32 keeps ~0.001 deg.
private _uAdvance = 2 * ([(360 * (_days - floor _days)) + (0.98564736629 * _days) - (_nodeRate * _days)] call _fnc_norm);

private _out = [];
{
    _x params ["_raan0", "_u0"];
    private _u = [_u0 + _uAdvance] call _fnc_norm;
    private _raan = _raan0 + _nodeRate * _days;
    private _xi = _a * ((cos _raan) * (cos _u) - (sin _raan) * (sin _u) * (cos _inc));
    private _yi = _a * ((sin _raan) * (cos _u) + (cos _raan) * (sin _u) * (cos _inc));
    private _zi = _a * (sin _u) * (sin _inc);
    private _sx = _xi * (cos _theta) + _yi * (sin _theta);
    private _sy = -_xi * (sin _theta) + _yi * (cos _theta);
    private _dx = _sx - _px;
    private _dy = _sy - _py;
    private _dz = _zi - _pz;
    private _l = sqrt (_dx * _dx + _dy * _dy + _dz * _dz);
    _dx = _dx / _l; _dy = _dy / _l; _dz = _dz / _l;
    private _east = -(sin _lon) * _dx + (cos _lon) * _dy;
    private _north = -(sin _lat) * (cos _lon) * _dx - (sin _lat) * (sin _lon) * _dy + (cos _lat) * _dz;
    private _up = (cos _lat) * (cos _lon) * _dx + (cos _lat) * (sin _lon) * _dy + (sin _lat) * _dz;
    if ((asin ((_up max -1) min 1)) >= _mask) then { _out pushBack [_east, _north, _up]; };
} forEach (_t get "slots");
_out
