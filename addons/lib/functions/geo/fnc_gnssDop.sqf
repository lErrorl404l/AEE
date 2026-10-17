#include "..\..\script_component.hpp"
/*
 * aee_lib_fnc_gnssDop
 *
 * Dilution of precision from the satellites actually received.  Pure.
 * With the line-of-sight rows g_i = [e_i, n_i, u_i, 1], the cofactor matrix
 * is Q = (G^T G)^-1 (GPS SPS PS 2020, App. A.8.2): the position error
 * covariance is UERE^2 Q, so the east, north and up variances and the
 * east-north covariance come straight from the geometry.  A blocked part of
 * the sky (a wall, a ridge, a canopy) removes rows and stretches the error
 * along the gap: the urban-canyon ellipse follows from the geometry.
 *
 * Arguments:
 *   0: ARRAY of [east, north, up] unit vectors (fnc_gnssSatellites, after
 *      any line-of-sight blocking).  A 4-element row [e, n, u, c] is used
 *      as given: [0, 0, 1, 0] is the altitude-hold constraint of a 2D fix.
 * Return: [count, qEE, qNN, qEN, qUU]; the q terms are -1 with fewer than 4
 *         satellites (no position solution).
 */
params [["_dirs", [], [[]]]];
private _n = count _dirs;
if (_n < 4) exitWith { [_n, -1, -1, -1, -1] };

// Normal matrix A = G^T G (4 x 4), row-major.
private _A = [];
for "_i" from 0 to 15 do { _A pushBack 0; };
{
    private _g = if ((count _x) > 3) then { _x } else { [_x select 0, _x select 1, _x select 2, 1] };
    for "_r" from 0 to 3 do {
        for "_c" from 0 to 3 do {
            _A set [_r * 4 + _c, (_A select (_r * 4 + _c)) + (_g select _r) * (_g select _c)];
        };
    };
} forEach _dirs;

// Gauss-Jordan inverse with partial pivoting.
private _I = [1,0,0,0, 0,1,0,0, 0,0,1,0, 0,0,0,1];
private _singular = false;
for "_c" from 0 to 3 do {
  if (!_singular) then {
    private _p = _c;
    for "_r" from (_c + 1) to 3 do {
        if (abs (_A select (_r * 4 + _c)) > abs (_A select (_p * 4 + _c))) then { _p = _r; };
    };
    if (abs (_A select (_p * 4 + _c)) < 1e-9) then { _singular = true; };
  };
  if (!_singular) then {
    private _p = _c;
    for "_r" from (_c + 1) to 3 do {
        if (abs (_A select (_r * 4 + _c)) > abs (_A select (_p * 4 + _c))) then { _p = _r; };
    };
    if (_p != _c) then {
        for "_k" from 0 to 3 do {
            private _t1 = _A select (_c * 4 + _k);
            _A set [_c * 4 + _k, _A select (_p * 4 + _k)];
            _A set [_p * 4 + _k, _t1];
            private _t2 = _I select (_c * 4 + _k);
            _I set [_c * 4 + _k, _I select (_p * 4 + _k)];
            _I set [_p * 4 + _k, _t2];
        };
    };
    private _pv = _A select (_c * 4 + _c);
    for "_k" from 0 to 3 do {
        _A set [_c * 4 + _k, (_A select (_c * 4 + _k)) / _pv];
        _I set [_c * 4 + _k, (_I select (_c * 4 + _k)) / _pv];
    };
    for "_r" from 0 to 3 do {
        if (_r != _c) then {
            private _f = _A select (_r * 4 + _c);
            for "_k" from 0 to 3 do {
                _A set [_r * 4 + _k, (_A select (_r * 4 + _k)) - _f * (_A select (_c * 4 + _k))];
                _I set [_r * 4 + _k, (_I select (_r * 4 + _k)) - _f * (_I select (_c * 4 + _k))];
            };
        };
    };
  };
};
if (_singular) exitWith { [_n, -1, -1, -1, -1] };
[_n, _I select 0, _I select 5, _I select 1, _I select 10]
