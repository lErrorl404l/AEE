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

Source (cutoff): the trapping wavelength for a surface duct with a linear
modified-refractivity profile is Kerr, D. E. (ed.), "Propagation of Short
Radio Waves", MIT Radiation Laboratory Series vol. 13, McGraw-Hill, 1951,
section 1-5 "The Modified Index", eq. (18):

    lambda_max = 0.014 * d^1.5     lambda_max in cm, d (duct height) in ft

Converted to SI (d in m):

    lambda_max = 0.014 * 3.28084^1.5 * d^1.5 cm = 8.32e-4 * d^1.5 m

Corroborated by the Naval Postgraduate School NWDC Electromagnetic Course,
module 4.2, which gives the minimum trapped frequency f_M = 360 * d^(-3/2)
GHz (1 GHz at d = 50 m, about 32 GHz at d = 5 m), i.e. lambda_max =
0.3 / f_M m = 8.33e-4 * d^1.5 m.  The earlier use of a bare
"0.085 * delta^1.5" as a metre-valued constant was Kerr's constant in
centimetres read as metres, a unit error of about 100x.

The gradient-dependent form is Bean, B. R., "Climatology of Ground-Based
Radio Ducts", NBS J. Res. D 63(1):29-34, 1959, eq. (13):
lambda_max = c * gamma^(1/2) * d^(3/2), with c = 2.514e2, lambda_max in cm
and gamma = ((N_t - N_d)/d - 15.7) x 10^-8.  This kernel does not take the
duct strength, so it uses the fixed linear-profile constant above.  For a
duct weaker than that profile the true cutoff wavelength is larger, so the
cutoff here is a lead for a weak duct.

SOURCE (trapping test): the M-profile test mirrors fnc_calculateRefraction's
refractivity gradient.  Verified vector: delta = 15 m ->
lambda_max = 8.32e-4 * 15^1.5 = 0.0483 m -> f_min = 6.2 GHz, so X-band is
trapped.

The exponent change itself is the issue's stated law.  The use of the SAME
(4 pi)^3 constant for the R^2 case is a simplification: the
cylindrical-spreading constant is not held (see fnc_radarRangeEquation).

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

// Trapping wavelength (Kerr 1951 sec 1-5 eq (18), 8.32e-4 delta^1.5 m):
//   f_min = c / lambda_max.  See the header for the corroborating source.
private _lambdaMax = 8.32e-4 * (_delta ^ 1.5);
private _fMin = 3e8 / _lambdaMax;
if (_freqHz < _fMin) exitWith { 4 };

2
