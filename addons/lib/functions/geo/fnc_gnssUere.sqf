#include "..\..\script_component.hpp"
/*
 * aee_lib_fnc_gnssUere
 *
 * Single-frequency GPS user range error, 1 sigma, metres.  Pure.
 *
 * Measured: the FAA SPS Performance Analysis Report #125 (Q1 2024) 95 %
 * horizontal errors of 34 sites, divided by twice the HDOP of the model
 * constellation at each site, tabulated by geomagnetic latitude
 * (fnc_gnssTables "uereBands"; tools/gen_gnss.py): ~1.2 m at mid latitudes,
 * ~4-5 m under the equatorial ionization anomaly, ~1.7 m in the auroral zone.
 * The ionospheric residual of the Klobuchar model dominates it, and the SPS
 * PS (2020, Table A.4-2) budgets that residual at 9.8 m at solar minimum and
 * 19.6 m at solar maximum: the measured value is scaled by
 * (1 + SSN / 179) / (1 + SSN_ref / 179), 179 the mean SILSO cycle maximum.
 *
 * Arguments:
 *   0: |geomagnetic latitude|, deg (NUMBER)
 *   1: sunspot number (NUMBER)
 * Return: UERE, metres, 1 sigma
 */
params [["_mlat", 45, [0]], ["_ssn", 100, [0]]];
private _t = call FUNC(gnssTables);
private _bands = _t get "uereBands";
private _m = abs _mlat;
private _u = (_bands select 0) select 1;
if (_m >= ((_bands select -1) select 0)) then {
    _u = (_bands select -1) select 1;
} else {
    for "_i" from 0 to ((count _bands) - 2) do {
        private _lo = _bands select _i;
        private _hi = _bands select (_i + 1);
        if (_m >= (_lo select 0) && _m <= (_hi select 0)) then {
            private _w = (_m - (_lo select 0)) / ((_hi select 0) - (_lo select 0));
            _u = ((_lo select 1) * (1 - _w)) + ((_hi select 1) * _w);
        };
    };
};
_u * (1 + ((_ssn max 0) / 179)) / (1 + ((_t get "ssnRef") / 179))
