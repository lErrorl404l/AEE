#include "..\..\script_component.hpp"
/*
Slope length-gradient LS factor (RUSLE, issue #21).

LS combines the effect of slope LENGTH and slope STEEPENESS on erosion. The
RUSLE unit plot is 22.13 m long on a 9 percent slope, where LS = 1.

Length factor (McCool et al. 1989, in USDA AH-703):

  L = (lambda / 22.13) ^ m
  m = beta / (1 + beta)
  beta = (sin(theta) / 0.0896) / (3.0 * sin(theta)^0.8 + 0.56)

Steepness factor (McCool et al. 1987, in USDA AH-703):

  S = 10.8 * sin(theta) + 0.03      slope < 9 percent
  S = 16.8 * sin(theta) - 0.50      slope >= 9 percent

theta is the slope angle, derived here from the slope as a fraction
(rise/run, m/m): sin(theta) = tan(theta) / sqrt(1 + tan(theta)^2).

Check: 10 percent slope, lambda = 50 m -> L = 1.53, S = 1.17, LS = 1.79.

Args:
  0: slope as a fraction (NUMBER, rise/run m/m, default 0)
  1: slope length lambda (NUMBER, metres, default 22.13)

Returns LS (dimensionless).

Example:
  [0.10, 50] call aee_hydrology_fnc_calculateSlopeLengthGradient -> 1.79
*/

params [["_slopeFraction", 0, [0]], ["_slopeLength", 22.13, [0]]];

if !(_slopeFraction isEqualType 0) then { _slopeFraction = 0; };
if !(_slopeLength isEqualType 0) then { _slopeLength = 22.13; };
_slopeFraction = _slopeFraction max 0;
_slopeLength = _slopeLength max 0.01;

// sin(theta) from the slope fraction.
private _sinTheta = _slopeFraction / (sqrt (1 + (_slopeFraction * _slopeFraction)));

// Length factor. A flat cell (sinTheta -> 0) makes beta -> 0, so m -> 0 and
// L -> 1: on flat ground slope length has no effect, which is correct.
private _beta = (_sinTheta / 0.0896) / ((3.0 * (_sinTheta ^ 0.8)) + 0.56);
private _m = _beta / (1 + _beta);
private _l = (_slopeLength / 22.13) ^ _m;

// Steepness factor.
private _slopePct = _slopeFraction * 100;
private _s = if (_slopePct < 9) then {
    (10.8 * _sinTheta) + 0.03
} else {
    (16.8 * _sinTheta) - 0.50
};

_l * _s
