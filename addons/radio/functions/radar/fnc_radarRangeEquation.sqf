#include "..\..\script_component.hpp"
/*
Radar range equation - monostatic maximum detection range.

  P_r   = P_t G^2 lambda^2 sigma / ( (4 pi)^3 R^4 )        [received power]
  R_max = [ P_t G^2 lambda^2 sigma / ( (4 pi)^3 P_min ) ]^(1/n)

  P_t      peak transmit power, W
  G        antenna gain (linear, not dB)
  lambda   wavelength, m
  sigma    target radar cross section, m^2
  P_min    minimum detectable power, W
  n        path-loss exponent: 4 in free space, 2 in a duct

Source: Skolnik, "Radar Handbook", 3rd ed., ch. 1 (monostatic radar range
equation); MIT Lincoln Laboratory, "Introduction to Radar Systems",
Lecture 4.  The two-way R^4 spreading term (4 pi)^3 is the standard form.

The ducted R^4 -> R^2 law (n = 2) is the issue's stated duct behaviour
(Kerr 1951).  The (4 pi)^3 constant is retained for the ducted case, which
is a simplification: the cylindrical-spreading constant for a duct is not
held.  UNSOURCED: the ducted constant.

Pure: reads no engine state, writes none.

Arguments:
  0: Number - peak transmit power P_t, W
  1: Number - antenna gain G, linear
  2: Number - wavelength lambda, m
  3: Number - target RCS sigma, m^2
  4: Number - minimum detectable power P_min, W
  5: Number - path-loss exponent n, default 4

Returns:
  Number - maximum detection range R_max, m
*/
params [
    ["_pt", 0, [0]],
    ["_gain", 1, [0]],
    ["_lambda", 0, [0]],
    ["_sigma", 0, [0]],
    ["_pmin", 0, [0]],
    ["_exponent", 4, [0]]
];

if (_pmin <= 0 || _lambda <= 0 || _gain <= 0) exitWith { 0 };

private _fourPiCubed = (4 * pi) ^ 3;
private _numerator = _pt * (_gain ^ 2) * (_lambda ^ 2) * _sigma;
private _denominator = _fourPiCubed * _pmin;

(_numerator / _denominator) ^ (1 / _exponent)
