#include "..\..\script_component.hpp"
/*
Convective available potential energy of a surface parcel.  Pure.

Parcel theory (Holton, An Introduction to Dynamic Meteorology, s.2.9):
  CAPE = integral over z of g (T_parcel - T_env) / T_env, where positive.
The parcel rises from the screen level dry-adiabatically (9.8 K/km) to its
lifting condensation level, the Bolton (1980, Mon Wea Rev 108:1046) eq. 15
temperature
  T_L = 1 / (1 / (T_d - 56) + ln(T / T_d) / 800) + 56,
then along the moist pseudo-adiabat
  Gamma_m = g (1 + L r_s / (R_d T)) / (c_p + L^2 r_s eps / (R_d T^2)).
The repository holds no sounding, so the environment is the ICAO standard
atmosphere lapse (6.5 K/km to 11 km, isothermal above; ICAO Doc 7488) from
the screen temperature.  A real afternoon superadiabatic layer and real
inversions aloft are not represented.
The parcel-theory updraft is w = sqrt(2 CAPE), an UPPER BOUND: entrainment
and water loading keep real updrafts below it (Peters et al. 2020, J Atmos
Sci 77:3747).

Arguments:
  0: Number - screen temperature, C
  1: Number - relative humidity, percent
  2: Number - surface pressure, hPa
Returns:
  Array - [CAPE J/kg, LCL height m, parcel-theory updraft m/s, LNB height m]
  The LNB (level of neutral buoyancy) is the top of the positive-buoyancy
  layer above the LCL, i.e. the convective cloud top.  It is 0 when the
  parcel is never buoyant above its LCL, so a consumer must treat 0 as
  "no convective top" (issue #238).
*/
params [["_tC", 15, [0]], ["_rh", 50, [0]], ["_ps", 1013.25, [0]]];
private _g = 9.80665;
private _rd = 287.04;
private _cp = 1004;
private _lv = 2.501e6;
private _eps = 0.622;
private _e = ((_rh max 1) / 100) * 6.112 * exp (17.67 * _tC / (_tC + 243.5));
private _lnE = ln (_e / 6.112);
private _tdC = 243.5 * _lnE / (17.67 - _lnE);
private _tk = _tC + 273.15;
private _tdk = _tdC + 273.15;
private _tl = 1 / ((1 / (_tdk - 56)) + ((ln (_tk / _tdk)) / 800)) + 56;
private _zl = (_tk - _tl) / 0.0098;

private _cape = 0;
// LNB: the highest level above the LCL at which the parcel is still warmer
// than the environment.  That height is the convective cloud top.
private _lnbM = 0;
private _tp = _tk;
private _dz = 50;
for "_k" from 0 to 320 do {
    private _z = _k * _dz;
    private _te = _tk - 0.0065 * (_z min 11000);
    private _p = if (_z < 11000) then {
        _ps * ((1 - 0.0065 * _z / _tk) ^ 5.2559)
    } else {
        _ps * ((1 - 0.0065 * 11000 / _tk) ^ 5.2559) * exp (-_g * (_z - 11000) / (_rd * (_tk - 71.5)))
    };
    if (_z <= _zl) then {
        _tp = _tk - 0.0098 * _z;
    } else {
        // Midpoint (second-order) step along the moist pseudo-adiabat.
        private _fnc_gm = {
            params ["_t", "_pp"];
            private _ews = 6.112 * exp (17.67 * (_t - 273.15) / ((_t - 273.15) + 243.5));
            private _rs = _eps * _ews / ((_pp - _ews) max 1);
            _g * (1 + (_lv * _rs / (_rd * _t))) / (_cp + ((_lv ^ 2) * _rs * _eps / (_rd * (_t ^ 2))))
        };
        // The step that crosses the LCL climbs dry to it, then moist.
        private _h = _dz;
        if ((_z - _dz) < _zl) then {
            _tp = _tl;
            _h = _z - _zl;
        };
        private _tMid = _tp - 0.5 * _h * ([_tp, _p] call _fnc_gm);
        _tp = _tp - _h * ([_tMid, _p] call _fnc_gm);
    };
    private _b = _g * (_tp - _te) / _te;
    if (_b > 0) then {
        _cape = _cape + _b * _dz;
        if (_z > _zl) then { _lnbM = _z; };
    };
};
[_cape, _zl, sqrt (2 * _cape), _lnbM]
