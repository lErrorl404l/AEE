#include "..\script_component.hpp"
/*
GENERATED FILE. Do not edit by hand.
Regenerate with: python3 tools/gen_wmm.py

Geomagnetic (centred-dipole) latitude of a point, from the WMM2025 degree-1
Gauss coefficients with their secular variation (data/magnetism/WMM2025.COF).
The north geomagnetic pole is at colatitude acos(-g10 / B0) and longitude
atan2(-h11, -g11), B0 = sqrt(g10^2 + g11^2 + h11^2) (the dipole axis).

Arguments: [latDeg, lonDeg, decimalYear]
Return: [geomagneticLatDeg, poleLatDeg, poleLonDeg]
Public: No
*/

params [["_latDeg", 0, [0]], ["_lonDeg", 0, [0]], ["_year", 2025, [0]]];
private _dt = _year - 2025;
private _cg10 = -29351.8 + (12) * _dt;
private _cg11 = -1410.8 + (9.7) * _dt;
private _ch11 = 4545.4 + (-21.5) * _dt;
private _b0 = sqrt (_cg10 * _cg10 + _cg11 * _cg11 + _ch11 * _ch11);
private _poleLat = 90 - acos (-_cg10 / _b0);
private _poleLon = (-_ch11) atan2 (-_cg11);
private _sinM = (sin _latDeg) * (sin _poleLat) + (cos _latDeg) * (cos _poleLat) * (cos (_lonDeg - _poleLon));
[asin ((_sinM max -1) min 1), _poleLat, _poleLon]
