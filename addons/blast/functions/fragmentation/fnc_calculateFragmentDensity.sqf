#include "..\..\script_component.hpp"

/*
Ground fragment density (density-based model, issue #107).

The areal fragment density on the ground for a warhead of N fragments and an
angular emission fraction f(theta):

  airburst (height h):  rho(R) = N * f(theta) * h / (4 * pi * s^3)
      s = sqrt(R^2 + h^2) is the slant range.  The extra h/s^2 is the
      cos(theta)/s^2 obliquity of a ground annulus seen from the burst:
      the ground range R = h tan(theta) and dR = h sec^2(theta) dtheta, so
      rho = (N f / 2) sin(theta) dtheta / (2 pi R dR) = N f h / (4 pi s^3).
      Falls as ~1/R^3 near the burst and as h/R^3 far from it.
  ground burst (h = 0): rho(R) = N * f(theta) / (2 * pi * R^2)
      falls as ~1/R^2, with a dead zone inside the burst radius

R is the ground range and h the burst height (0 for a ground burst).

Input:  [_fragmentCount, _angularFraction, _rangeM, _burstHeightM]
Output: areal fragment density (fragments per m^2)
*/
params [
    ["_fragmentCount", 1, [0]],
    ["_angularFraction", 1, [0]],
    ["_rangeM", 10, [0]],
    ["_burstHeightM", 0, [0]]
];

if (_fragmentCount <= 0 || _rangeM <= 0) exitWith { 0 };

private _n = _fragmentCount * _angularFraction;
if (_burstHeightM > 0) exitWith {
    private _s = sqrt ((_rangeM * _rangeM) + (_burstHeightM * _burstHeightM));
    _n * _burstHeightM / (4 * pi * _s * _s * _s)
};
_n / (2 * pi * _rangeM * _rangeM)
