#include "..\..\script_component.hpp"
/*
Evaporation-duct trapping test and the trapped range law.

An evaporation duct traps SHF energy when two conditions hold:

  1. The modified refractivity decreases with height: dM/dz < 0, where
     M = N + 0.157 z (z in m).  A surface duct is present.
  2. The frequency is above the duct cutoff: lambda_max = 0.085 delta^1.5
     (delta = duct height, m).  X-band and above are always trapped.

Inside a duct both endpoints lie below delta and the two-way spreading
is cylindrical, so the range law becomes R^2 (one-way) instead of R^4
(two-way spherical).  This function returns the path-loss exponent to
use: 2 when trapped, 4 otherwise.

Source: Kerr, D. E. (ed.), "Propagation of Short Radio Waves", MIT
Radiation Laboratory Series, 1951 (the duct cutoff).  The SHF duct
finding is issue #37; the M-profile test mirrors fnc_calculateRefraction's
refractivity gradient.  Verified vector: delta = 15 m -> lambda_max =
0.085 * 15^1.5 = 4.94 m -> f_min = 60.7 MHz, so X-band is trapped.

UNSOURCED: the use of the SAME (4 pi)^3 constant for the R^2 case (the
cylindrical-spreading constant is not held).  The exponent change itself
is the issue's stated law.

Pure: reads no engine state, writes none.

Arguments:
  0: Number - duct height delta, m
  1: Number - frequency, Hz
  2: Number - refractivity gradient dN/dz, N/km
  3: Number - antenna height, m
  4: Number - target height, m

Returns:
  Number - path-loss exponent: 2 when trapped, else 4
*/
params [
    ["_delta", 0, [0]],
    ["_freqHz", 0, [0]],
    ["_gradient", 0, [0]],
    ["_ha", 0, [0]],
    ["_ht", 0, [0]]
];

// Modified-refractivity gradient: dM/dz = dN/dz + 0.157 (N per m).
// _gradient is N per km, so convert 0.157 N/m -> 157 N/km.
private _dMdz = _gradient + 157;
if (_dMdz >= 0) exitWith { 4 };

if (_delta <= 0) exitWith { 4 };

// Both endpoints must lie below the duct height.
if (_ha > _delta || _ht > _delta) exitWith { 4 };

// Cutoff wavelength: lambda_max = 0.085 * delta^1.5, f_min = c / lambda_max.
private _lambdaMax = 0.085 * (_delta ^ 1.5);
private _fMin = 3e8 / _lambdaMax;
if (_freqHz < _fMin) exitWith { 4 };

2
