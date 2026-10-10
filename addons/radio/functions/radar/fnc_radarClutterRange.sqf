#include "..\..\script_component.hpp"
/*
Clutter-limited detection range.

  R_max = sigma_t / ( sigma0 * theta_az * (c tau / 2) * sec(psi) * TCR_min )

  sigma_t   target radar cross section, m^2
  sigma0    clutter reflectivity, linear (10^(sigma0_dB/10))
  theta_az  azimuth beamwidth, rad
  c tau / 2 range-cell depth, m (c = 3e8 m/s)
  psi       grazing angle, degrees
  TCR_min   target-to-clutter ratio for detection

The clutter-limited range is power-independent: the target echo and the
clutter return scale together with the transmit power.

Source: Gregers-Hansen & Mital, NRL 2012 (DTIC ADA559494); Skolnik,
"Radar Handbook", 3rd ed.  Verified vector: sigma_t = 10, sigma0 = -40 dB,
theta_az = 0.02 rad, tau = 1e-6 s, TCR_min = 10 -> 3.3 km.

Pure: reads no engine state, writes none.

Arguments:
  0: Number - target RCS sigma_t, m^2
  1: Number - clutter reflectivity sigma0, dB
  2: Number - azimuth beamwidth theta_az, rad
  3: Number - pulse width tau, s
  4: Number - grazing angle psi, degrees
  5: Number - target-to-clutter ratio TCR_min

Returns:
  0: Number - clutter-limited range R_max, m
*/
params [
    ["_sigmaT", 0, [0]],
    ["_sigma0Db", 0, [0]],
    ["_thetaAz", 0, [0]],
    ["_tau", 0, [0]],
    ["_psi", 0, [0]],
    ["_tcrMin", 1, [0]]
];

private _c = 3e8;
private _sigma0 = 10 ^ (_sigma0Db / 10);
private _cellDepth = _c * _tau / 2;
private _secPsi = 1 / ((cos _psi) max 1e-9);
private _denom = _sigma0 * _thetaAz * _cellDepth * _secPsi * _tcrMin;

if (_denom <= 0) exitWith { 0 };

_sigmaT / _denom
