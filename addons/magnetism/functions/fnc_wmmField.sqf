#include "..\script_component.hpp"
/*
GENERATED FILE. Do not edit by hand.
Regenerate with: python3 tools/gen_wmm.py

World Magnetic Model WMM2025 (NOAA NCEI / BGS, public domain), epoch
2025, valid 2025.0-2030.0.  Coefficients from data/magnetism/WMM2025.COF.
The generator executes this kernel on every NOAA test value before writing.

Arguments:
  0: geodetic latitude, deg (positive north)
  1: longitude, deg (positive east)
  2: height above the WGS84 ellipsoid, km
  3: decimal year
Return: [D declination deg (east +), I inclination deg (down +), H, X, Y, Z nT]
At |lat| = 90 exactly (a geographic pole) the frame has no east, so D, H, X
and Y are undefined and are returned as 0, I is +90 (north) or -90 (south)
and Z, the axial component, is exact.
Public: No
*/

params [["_latDeg", 0, [0]], ["_lonDeg", 0, [0]], ["_altKm", 0, [0]], ["_year", 2025, [0]]];

// Gauss coefficients for n = 1..12, m = 0..n, flattened in (n, m) order.
private _coefG = [-29351.8, -1410.8, -2556.6, 2951.1, 1649.3, 1361, -2404.1, 1243.8, 453.6, 895, 799.5, 55.7, -281.1, 12.1, -233.2, 368.9, 187.2, -138.7, -142, 20.9, 64.4, 63.8, 76.9, -115.7, -40.9, 14.9, -60.7, 79.5, -77, -8.8, 59.3, 15.8, 2.5, -11.1, 14.2, 23.2, 10.8, -17.5, 2, -21.7, 16.9, 15, -16.8, 0.9, 4.6, 7.8, 3, -0.2, -2.5, -13.1, 2.4, 8.6, -8.7, -12.9, -1.3, -6.4, 0.2, 2, -1, -0.6, -0.9, 1.5, 0.9, -2.7, -3.9, 2.9, -1.5, -2.5, 2.4, -0.6, -0.1, -0.6, -0.1, 1.1, -1, -0.2, 2.6, -2, -0.2, 0.3, 1.2, -1.3, 0.6, 0.6, 0.5, -0.1, -0.4, -0.2, -1.3, -0.7];
private _coefH = [0, 4545.4, 0, -3133.6, -815.1, 0, -56.6, 237.5, -549.5, 0, 278.6, -133.9, 212, -375.6, 0, 45.4, 220.2, -122.9, 43, 106.1, 0, -18.4, 16.8, 48.8, -59.8, 10.9, 72.7, 0, -48.9, -14.4, -1, 23.4, -7.4, -25.1, -2.3, 0, 7.1, -12.6, 11.4, -9.7, 12.7, 0.7, -5.2, 3.9, 0, -24.8, 12.2, 8.3, -3.3, -5.2, 7.2, -0.6, 0.8, 10, 0, 3.3, 0, 2.4, 5.3, -9.1, 0.4, -4.2, -3.8, 0.9, -9.1, 0, 0, 2.9, -0.6, 0.2, 0.5, -0.3, -1.2, -1.7, -2.9, -1.8, -2.3, 0, -1.3, 0.7, 1, -1.4, -0, 0.6, -0.1, 0.8, 0.1, -1, 0.1, 0.2];
private _coefGD = [12, 9.7, -11.6, -5.2, -8, -1.3, -4.2, 0.4, -15.6, -1.6, -2.4, -6, 5.6, -7, 0.6, 1.4, 0, 0.6, 2.2, 0.9, -0.2, -0.4, 0.9, 1.2, -0.9, 0.3, 0.9, -0, -0.1, -0.1, 0.5, -0.1, -0.8, -0.8, 0.8, -0.1, 0.2, 0, 0.5, -0.1, 0.3, 0.2, -0, 0.2, -0, -0.1, 0.1, 0.3, -0.3, 0, 0.3, -0.1, 0.1, -0.1, 0.1, 0, 0.1, 0.1, -0, -0.3, 0, -0.1, -0.1, -0, -0, 0, -0, 0, 0, 0, -0.1, 0, -0, -0.1, -0.1, -0.1, -0.1, 0, 0, -0, -0, -0, -0, 0.1, -0, 0, 0, -0.1, -0, -0.1];
private _coefHD = [0, -21.5, 0, -27.7, -12.1, 0, 4, -0.3, -4.1, 0, -1.1, 4.1, 1.6, -4.4, 0, -0.5, 2.2, 0.4, 1.7, 1.9, 0, 0.3, -1.6, -0.4, 0.9, 0.7, 0.9, 0, 0.6, 0.5, -0.8, 0, -1, 0.6, -0.2, 0, -0.2, 0.5, -0.4, 0.4, -0.5, -0.6, 0.3, 0.2, 0, -0.3, 0.3, -0.3, 0.3, 0.2, -0.1, -0.2, 0.4, 0.1, 0, 0, -0, -0.2, 0.1, -0.1, 0.1, 0, -0.1, 0.2, -0, 0, -0, 0.1, -0, 0.1, -0, -0, 0.1, -0, 0, 0, 0, 0, -0, 0, -0.1, 0.1, -0, -0, -0, 0, -0, -0, 0, -0.1];

private _dt = _year - 2025;

// WGS84 geodetic -> geocentric.
private _a = 6378.137;
private _f = 1 / 298.257223563;
private _e2 = _f * (2 - _f);
private _sinLat = sin _latDeg;
private _cosLat = cos _latDeg;
private _Nr = _a / sqrt (1 - _e2 * _sinLat * _sinLat);
private _p = (_Nr + _altKm) * _cosLat;
private _z = (_Nr * (1 - _e2) + _altKm) * _sinLat;
private _r = sqrt (_p * _p + _z * _z);
private _latC = _z atan2 _p;
private _ct = sin _latC;
private _st = cos _latC;
// Geographic poles: cos(latC) is zero, every P(n,m) with m > 0 vanishes with
// it, and the (north, east) frame has no defined orientation there.  The
// division below would then be 0/0, whose float32 value is pure rounding
// noise, so the pole takes the overridden path at the end of the kernel.
private _atPole = (abs _st) < 1e-6;
private _stSafe = [_st, 1] select _atPole;

// Schmidt semi-normalised P(n,m) and dP/dtheta, flat index n(n+1)/2 + m.
private _pnm = [1];
private _dpnm = [0];
for "_n" from 1 to 12 do {
    for "_m" from 0 to _n do {
        if (_n == _m) then {
            private _k = 1;
            if (_n > 1) then { _k = sqrt ((2 * _n - 1) / (2 * _n)); };
            private _iPrev = ((_n - 1) * _n / 2) + _n - 1;
            _pnm pushBack (_k * _st * (_pnm select _iPrev));
            _dpnm pushBack (_k * (_ct * (_pnm select _iPrev) + _st * (_dpnm select _iPrev)));
        } else {
            private _a1 = (2 * _n - 1) / sqrt (_n * _n - _m * _m);
            private _i1 = ((_n - 1) * _n / 2) + _m;
            private _pn = _a1 * _ct * (_pnm select _i1);
            private _dpn = _a1 * (_ct * (_dpnm select _i1) - _st * (_pnm select _i1));
            if (_n > 1) then {
                private _b1 = sqrt ((((_n - 1) * (_n - 1)) - _m * _m) / (_n * _n - _m * _m));
                private _i2 = ((_n - 2) * (_n - 1) / 2) + _m;
                _pn = _pn - _b1 * (_pnm select _i2);
                _dpn = _dpn - _b1 * (_dpnm select _i2);
            };
            _pnm pushBack _pn;
            _dpnm pushBack _dpn;
        };
    };
};

// Spherical-harmonic sum (geocentric north X', east Y', down Z').
private _bx = 0;
private _by = 0;
private _bz = 0;
private _k = 0;
for "_n" from 1 to 12 do {
    private _rr = (6371.2 / _r) ^ (_n + 2);
    for "_m" from 0 to _n do {
        private _g = (_coefG select _k) + (_coefGD select _k) * _dt;
        private _h = (_coefH select _k) + (_coefHD select _k) * _dt;
        private _cm = cos (_m * _lonDeg);
        private _sm = sin (_m * _lonDeg);
        private _ip = (_n * (_n + 1) / 2) + _m;
        _bx = _bx + _rr * (_g * _cm + _h * _sm) * (_dpnm select _ip);
        _by = _by + _rr * _m * (_g * _sm - _h * _cm) * (_pnm select _ip) / _stSafe;
        _bz = _bz - (_n + 1) * _rr * (_g * _cm + _h * _sm) * (_pnm select _ip);
        _k = _k + 1;
    };
};

// Rotate to the geodetic frame.
private _d = _latC - _latDeg;
private _Xg = _bx * (cos _d) - _bz * (sin _d);
private _Zg = _bx * (sin _d) + _bz * (cos _d);
if (_atPole) then {
    // Pole: the declination and the horizontal intensity have no defined value
    // (the frame has no east), so report them as 0.  The axial component Z is
    // exact and is kept: I is then +90 at the north pole and -90 at the south.
    _by = 0;
    _Xg = 0;
};
private _Hn = sqrt (_Xg * _Xg + _by * _by);
[_by atan2 _Xg, _Zg atan2 _Hn, _Hn, _Xg, _by, _Zg]
