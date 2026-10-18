#include "..\..\script_component.hpp"
/*
Turbulent kinetic energy dissipation rate in the atmospheric boundary layer,
and the eddy dissipation rate EDR = epsilon^1/3 (ICAO Annex 3).  Pure.

Surface layer, Monin-Obukhov similarity (Kaimal & Finnigan 1994, Atmospheric
Boundary Layer Flows, s.1.6; Wyngaard & Cote 1971):
  u* = kappa U10 / ln(10 / z0)                 (neutral log law, kappa 0.4)
  H  = rho c_p C_H U10 (T_s - T_a),  C_H = kappa^2 / (ln(10/z0) ln(10/z0h)),
       z0h = z0 / 10 (Garratt 1992, The Atmospheric Boundary Layer, s.4.2)
  L  = - u*^3 T rho c_p / (kappa g H)           (Obukhov length)
  epsilon = u*^3 phi_e(z/L) / (kappa z),
    phi_e = (1 + 0.5 |z/L|^(2/3))^(3/2)  unstable,  1 + 5 z/L  stable (z/L <= 1)
Mixed layer, convective scaling (Kaimal et al. 1976, J Atmos Sci 33:2152):
  w* = (g H z_i / (rho c_p T))^(1/3),  epsilon = 0.4 w*^3 / z_i  for
  0.1 z_i < z < z_i, the convective-layer top z_i supplied by the caller.
Optical turbulence at the same height (Wyngaard, Izumi & Collins 1971,
J Opt Soc Am 61:1646): T* = -H / (rho c_p u*),
  C_T^2 = 4.9 T*^2 z^-2/3 (1 - 7 z/L)^-2/3   unstable,
          4.9 T*^2 z^-2/3 (1 + 2.4 (z/L)^2/3) stable,
and the optical structure constant Cn^2 = (79e-6 P / T^2)^2 C_T^2
(P in hPa, T in K).
Neutral and stable boundary-layer depth h = 0.25 u* / f (Garratt 1992,
s.6.1), f = 2 Omega sin(latitude).  Above the boundary layer the clear-air
dissipation is taken as zero.

Arguments:
  0: Number - 10 m wind speed, m/s
  1: Number - height above ground, m
  2: Number - roughness length z0, m
  3: Number - surface minus air temperature, K
  4: Number - air temperature, C
  5: Number - air density, kg/m3
  6: Number - latitude, deg
  7: Number - convective boundary-layer top z_i, m (the LCL by day)
  8: Number - pressure, hPa
Returns:
  Array - [epsilon m2/s3, EDR m^(2/3)/s, Obukhov length m, u* m/s,
           Cn^2 m^-2/3]
*/
params [
    ["_u10", 5, [0]], ["_zIn", 2, [0]], ["_z0", 0.03, [0]], ["_dT", 0, [0]],
    ["_tC", 15, [0]], ["_rho", 1.225, [0]], ["_lat", 45, [0]], ["_zi", 1000, [0]],
    ["_pHpa", 1013.25, [0]]
];
private _k = 0.4;
private _g = 9.80665;
private _cp = 1004;
private _z0c = (_z0 max 0.0001) min 3;
private _u = _u10 max 0.1;
private _z = _zIn max (10 * _z0c) max 2;
private _tK = _tC + 273.15;
private _lnM = ln (10 / _z0c);
private _ustar = _k * _u / _lnM;
private _ch = (_k ^ 2) / (_lnM * (ln (10 / (_z0c / 10))));
private _h = _rho * _cp * _ch * _u * _dT;
private _lObu = if ((abs _h) > 1e-6) then { -((_ustar ^ 3) * _tK * _rho * _cp) / (_k * _g * _h) } else { 1e9 };
private _zeta = _z / _lObu;
private _phi = if (_zeta < 0) then { (1 + 0.5 * ((abs _zeta) ^ (2 / 3))) ^ 1.5 } else { 1 + 5 * (_zeta min 1) };
private _f = 2 * 7.2921e-5 * (abs (sin _lat)) max 1e-5;
private _hNeutral = 0.25 * _ustar / _f;
private _eps = 0;
if (_h > 0) then {
    private _zic = _zi max 100;
    private _wStar = ((_g * _h * _zic) / (_rho * _cp * _tK)) ^ (1 / 3);
    if (_z <= 0.1 * _zic) then {
        _eps = (_ustar ^ 3) * _phi / (_k * _z);
    } else {
        if (_z <= _zic) then { _eps = 0.4 * (_wStar ^ 3) / _zic; };
    };
} else {
    if (_z <= _hNeutral) then { _eps = (_ustar ^ 3) * _phi / (_k * _z); };
};
private _tStar = -_h / (_rho * _cp * _ustar);
private _ct2 = 4.9 * (_tStar ^ 2) * (_z ^ (-2 / 3));
if (_zeta < 0) then { _ct2 = _ct2 * ((1 - 7 * _zeta) ^ (-2 / 3)); } else { _ct2 = _ct2 * (1 + 2.4 * ((_zeta min 1) ^ (2 / 3))); };
private _cn2 = ((79e-6 * _pHpa / (_tK ^ 2)) ^ 2) * _ct2;
[_eps, _eps ^ (1 / 3), _lObu, _ustar, _cn2]
