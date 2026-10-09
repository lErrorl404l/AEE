#include "..\..\script_component.hpp"
/*
 * aee_lib_fnc_utmToLatLon
 *
 * Inverse WGS84 / UTM projection.  Pure and argument-driven: it reads no
 * world, no config and no player.
 *
 * The inverse series is the transverse Mercator expansion in DMA TM 8358.2,
 * "The Universal Grids: UTM and UPS", Ed.1 1989, chapters 2 and 3, with the
 * WGS84 ellipsoid of NIMA TR8350.2:
 *   a  = 6378137 m, 1/f = 298.257223563, e2 = f(2-f), e'2 = e2/(1-e2)
 *   k0 = 0.9996, false easting 500000 m, false northing 10000000 m south
 *
 * Arguments:
 *   0: easting    <NUMBER> UTM easting, metres
 *   1: northing   <NUMBER> UTM northing, metres (southern carries +10000000)
 *   2: zone       <NUMBER> UTM zone number, 1..60
 *   3: hemisphere <STRING> "north" or "south"
 *
 * Return: [latDeg, lonDeg]
 */
params [
    ["_easting", 500000, [0]],
    ["_northing", 0, [0]],
    ["_zone", 31, [0]],
    ["_hemisphere", "north", [""]]
];

private _a = 6378137;
private _invF = 298.257223563;
private _f = 1 / _invF;
private _e2 = _f * (2 - _f);
private _ep2 = _e2 / (1 - _e2);
private _k0 = 0.9996;
private _fnSouth = 10000000;

if (_zone < 1) then { _zone = 1; };
if (_zone > 60) then { _zone = 60; };

private _x = _easting - 500000;
private _y = _northing;
if (_hemisphere == "south") then { _y = _y - _fnSouth; };

private _e4 = _e2 * _e2;
private _e6 = _e4 * _e2;

private _M = _y / _k0;
private _mu = _M / (_a * (1 - _e2 / 4 - 3 * _e4 / 64 - 5 * _e6 / 256));
private _e1 = (1 - (sqrt (1 - _e2))) / (1 + (sqrt (1 - _e2)));

// SQF trig takes degrees; the series sin arguments use mu in degrees.
private _muDeg = _mu * 180 / pi;

private _phi1 =
    _mu
    + (3 * _e1 / 2 - 27 * (_e1 ^ 3) / 32) * (sin (2 * _muDeg))
    + (21 * (_e1 ^ 2) / 16 - 55 * (_e1 ^ 4) / 32) * (sin (4 * _muDeg))
    + (151 * (_e1 ^ 3) / 96) * (sin (6 * _muDeg))
    + (1097 * (_e1 ^ 4) / 512) * (sin (8 * _muDeg));

private _phi1Deg = _phi1 * 180 / pi;
private _sinPhi1 = sin _phi1Deg;
private _cosPhi1 = cos _phi1Deg;
private _tanPhi1 = tan _phi1Deg;

private _C1 = _ep2 * _cosPhi1 * _cosPhi1;
private _T1 = _tanPhi1 * _tanPhi1;
private _N1 = _a / (sqrt (1 - _e2 * _sinPhi1 * _sinPhi1));
private _R1 = _a * (1 - _e2) / ((1 - _e2 * _sinPhi1 * _sinPhi1) ^ 1.5);
private _D = _x / (_N1 * _k0);

private _lat = _phi1 - (_N1 * _tanPhi1 / _R1) * (
    (_D * _D) / 2
    - (5 + 3 * _T1 + 10 * _C1 - 4 * _C1 * _C1 - 9 * _ep2) * (_D ^ 4) / 24
    + (61 + 90 * _T1 + 298 * _C1 + 45 * _T1 * _T1 - 252 * _ep2 - 3 * _C1 * _C1) * (_D ^ 6) / 720
);

private _lon0 = (_zone * 6) - 183;
private _lon = (_lon0 * pi / 180) + (
    _D
    - (1 + 2 * _T1 + _C1) * (_D ^ 3) / 6
    + (5 - 2 * _C1 + 28 * _T1 - 3 * _C1 * _C1 + 8 * _ep2 + 24 * _T1 * _T1) * (_D ^ 5) / 120
) / _cosPhi1;

[_lat * 180 / pi, _lon * 180 / pi]
