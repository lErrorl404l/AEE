#include "..\..\script_component.hpp"
/*
 * aee_core_fnc_latLonToUtm
 *
 * Forward WGS84 / UTM projection.  Pure and argument-driven: it reads no
 * world, no config and no player.
 *
 * The series is the transverse Mercator expansion in DMA TM 8358.2, "The
 * Universal Grids: UTM and UPS", Ed.1 1989, chapters 2 and 3, with the WGS84
 * ellipsoid of NIMA TR8350.2:
 *   a  = 6378137 m, 1/f = 298.257223563, e2 = f(2-f), e'2 = e2/(1-e2)
 *   k0 = 0.9996, false easting 500000 m, false northing 0 north / 10000000 south
 * The zone number, the latitude band and the 100 km letters are defined by
 * the NGA MGRS guidance (Modified February 2009).
 *
 * Arguments:
 *   0: latDeg <NUMBER> latitude, degrees, positive north
 *   1: lonDeg <NUMBER> longitude, degrees, positive east
 *
 * Return: [easting, northing, zone, hemisphereToken]
 *   hemisphereToken is "north" or "south".  The northing carries the
 *   10000000 false northing in the southern hemisphere.
 */
params [
    ["_latDeg", 0, [0]],
    ["_lonDeg", 0, [0]]
];

private _a = 6378137;
private _invF = 298.257223563;
private _f = 1 / _invF;
private _e2 = _f * (2 - _f);
private _ep2 = _e2 / (1 - _e2);
private _k0 = 0.9996;
private _fe = 500000;
private _fnSouth = 10000000;

private _zone = (floor ((_lonDeg + 180) / 6)) + 1;
if (_zone < 1) then { _zone = 1; };
if (_zone > 60) then { _zone = 60; };

// SQF trig takes degrees, so the angles stay in degrees for sin/cos/tan.
// The series arguments A, M use radians.
private _lon0 = (_zone * 6) - 183;
private _phiRad = _latDeg * pi / 180;

private _sinPhi = sin _latDeg;
private _cosPhi = cos _latDeg;
private _tanPhi = tan _latDeg;

private _e4 = _e2 * _e2;
private _e6 = _e4 * _e2;

private _N = _a / (sqrt (1 - _e2 * _sinPhi * _sinPhi));
private _T = _tanPhi * _tanPhi;
private _C = _ep2 * _cosPhi * _cosPhi;
private _A = (_lonDeg - _lon0) * (pi / 180) * _cosPhi;

private _M = _a * (
    (1 - _e2 / 4 - 3 * _e4 / 64 - 5 * _e6 / 256) * _phiRad
    - (3 * _e2 / 8 + 3 * _e4 / 32 + 45 * _e6 / 1024) * (sin (2 * _latDeg))
    + (15 * _e4 / 256 + 45 * _e6 / 1024) * (sin (4 * _latDeg))
    - (35 * _e6 / 3072) * (sin (6 * _latDeg))
);

private _easting = _fe + _k0 * _N * (
    _A + (1 - _T + _C) * (_A ^ 3) / 6
    + (5 - 18 * _T + _T * _T + 72 * _C - 58 * _ep2) * (_A ^ 5) / 120
);

private _northing = _k0 * (
    _M + _N * _tanPhi * (
        (_A * _A) / 2
        + (5 - _T + 9 * _C + 4 * _C * _C) * (_A ^ 4) / 24
        + (61 - 58 * _T + _T * _T + 600 * _C - 330 * _ep2) * (_A ^ 6) / 720
    )
);

private _hemisphere = "north";
if (_latDeg < 0) then {
    _hemisphere = "south";
    _northing = _northing + _fnSouth;
};

[_easting, _northing, _zone, _hemisphere]
