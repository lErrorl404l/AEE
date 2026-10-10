#include "..\script_component.hpp"

/*
Single knife-edge diffraction loss (issue #13).

An obstacle that cuts the direct line between the two path ends diffracts the
wave into the shadow behind it.  The Fresnel-Kirchhoff diffraction parameter
is
    v = h * sqrt(2*(d1+d2)/(lambda*d1*d2))
and the approximate diffraction loss (valid for v > -0.78) is
    L = 6.9 + 20*log10(sqrt((v-0.1)^2 + 1) + v - 0.1)   dB
For v <= -0.78 the obstacle clears the path and the loss is 0 dB.

SOURCE: ITU-R P.526, section 4.1 (single knife-edge diffraction), equation
(26) for v and equation (31) for L.  Current edition P.526-16 (11/2025);
P.526-15 (10/2019) carries the same numbering.  URL:
https://www.itu.int/rec/R-REC-P.526/en
Definitions (section 4.1, verbatim): h is the height of the obstacle top
above the straight line joining the two path ends (negative when below);
d1 and d2 are the distances from the obstacle top to each end; lambda is the
wavelength.

Args:
  0: h        <NUMBER> obstacle height above the direct line, m
  1: d1       <NUMBER> distance from the first end to the obstacle, m
  2: d2       <NUMBER> distance from the obstacle to the second end, m
  3: frequency <NUMBER> carrier, Hz

Return: <NUMBER> diffraction loss, dB (0 when the path is clear).
*/

params [
    ["_h", 0, [0]],
    ["_d1", 1000, [0]],
    ["_d2", 1000, [0]],
    ["_freqHz", 1e8, [0]]
];

private _lambda = 3e8 / (_freqHz max 1);
private _dA = _d1 max 1;
private _dB = _d2 max 1;

// Fresnel-Kirchhoff diffraction parameter, P.526-16 eq (26).
private _v = _h * (sqrt ((2 * (_dA + _dB)) / (_lambda * _dA * _dB)));

// Below the validity bound the obstacle clears the direct line: no loss.
if (_v <= -0.78) exitWith { 0 };

// P.526-16 eq (31), valid for v > -0.78.
6.9 + (20 * (log ((sqrt (((_v - 0.1) ^ 2) + 1)) + _v - 0.1)))
