#include "..\..\script_component.hpp"
/*
 * aee_lib_fnc_bullingtonLoss
 *
 * Diffraction loss over a terrain profile, ITU-R P.526-15 s.4.5.1 (the
 * Bullington construction).  Pure.
 *
 * Every intermediate point is raised by the Earth bulge 500 Ce d_i (d - d_i),
 * Ce = 1/8500 km^-1 (the effective Earth radius of 8 500 km, k = 4/3,
 * P.526-15 s.1).  On a line-of-sight path (eqs. 49-52) the loss is J of the largest
 * Fresnel-Kirchhoff parameter nu; on a trans-horizon path the two
 * steepest-slope lines from the antennas meet at the Bullington point, and
 * J is taken of its nu (eqs. 53-56).  Then
 *   J(nu) = 6.9 + 20 log10(sqrt((nu - 0.1)^2 + 1) + nu - 0.1)   nu > -0.78  (eq. 31)
 *   Lb    = Luc + (1 - exp(-Luc / 6)) (10 + 0.02 d)            (eq. 57)
 *
 * Arguments:
 *   0: d     <NUMBER> path length, km
 *   1: dist  <ARRAY>  distances of the intermediate profile points, km
 *   2: hgt   <ARRAY>  their heights above sea level, m
 *   3: hts   <NUMBER> transmit antenna height above sea level, m
 *   4: hrs   <NUMBER> receive antenna height above sea level, m
 *   5: fMHz  <NUMBER> frequency, MHz
 * Return: diffraction loss, dB (0 on a clear path)
 */
params [["_d", 1, [0]], ["_dist", [], [[]]], ["_hgt", [], [[]]], ["_hts", 0, [0]], ["_hrs", 0, [0]], ["_fMHz", 100, [0]]];
private _n = (count _dist) min (count _hgt);
if (_n < 1 || _d <= 0) exitWith { 0 };
private _ce = 1 / 8500;
private _lambda = 299.792458 / _fMHz;
private _fnc_J = {
    params ["_nu"];
    if (_nu <= -0.78) then { 0 } else {
        6.9 + 20 * log ((sqrt (((_nu - 0.1) ^ 2) + 1)) + _nu - 0.1)
    };
};
private _stim = -1e9;
private _srim = -1e9;
private _bulged = [];
for "_i" from 0 to (_n - 1) do {
    private _di = _dist select _i;
    private _hi = (_hgt select _i) + 500 * _ce * _di * (_d - _di);
    _bulged pushBack _hi;
    if (_di > 0 && _di < _d) then {
        _stim = _stim max ((_hi - _hts) / _di);
        _srim = _srim max ((_hi - _hrs) / (_d - _di));
    };
};
if (_stim < -1e8) exitWith { 0 };
private _str = (_hrs - _hts) / _d;
private _luc = 0;
if (_stim < _str) then {
    // Line of sight: the largest diffraction parameter.
    private _numax = -1e9;
    for "_i" from 0 to (_n - 1) do {
        private _di = _dist select _i;
        if (_di > 0 && _di < _d) then {
            private _clear = (_bulged select _i) - ((_hts * (_d - _di)) + (_hrs * _di)) / _d;
            _numax = _numax max (_clear * sqrt ((0.002 * _d) / (_lambda * _di * (_d - _di))));
        };
    };
    _luc = [_numax] call _fnc_J;
} else {
    // Trans-horizon: the Bullington point.
    private _dbp = ((_hrs - _hts) + (_srim * _d)) / ((_stim + _srim) max 1e-9);
    _dbp = (_dbp max 1e-4) min (_d - 1e-4);
    private _nub = ((_hts + (_stim * _dbp)) - ((_hts * (_d - _dbp)) + (_hrs * _dbp)) / _d)
        * sqrt ((0.002 * _d) / (_lambda * _dbp * (_d - _dbp)));
    _luc = [_nub] call _fnc_J;
};
_luc + (1 - exp (-_luc / 6)) * (10 + 0.02 * _d)
