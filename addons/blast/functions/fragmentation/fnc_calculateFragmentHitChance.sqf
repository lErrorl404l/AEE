#include "..\..\script_component.hpp"

/*
Fragment hit probability (Poisson density model, issue #107).

For an areal fragment density rho and a target presented area A, the mean
number of fragment hits is lambda = rho * A.  Under the Poisson assumption the
probability of at least one hit is:

  P_hit = 1 - exp(-lambda)

Input:  [_density, _areaM2]
Output: probability of at least one fragment hit (0-1)
*/
params [
    ["_density", 1, [0]],
    ["_areaM2", 0.25, [0]]
];

if (_density <= 0 || _areaM2 <= 0) exitWith { 0 };

private _lambda = _density * _areaM2;
(1 - exp (-_lambda)) min 1 max 0
