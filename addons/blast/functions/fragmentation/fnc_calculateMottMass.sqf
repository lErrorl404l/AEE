#include "..\..\script_component.hpp"

/*
Mott fragment-size distribution, inverse-CDF sample (Mott 1943, 1947).

Draws one fragment mass from the Mott distribution.  With mu the Mott
parameter (M_casing / (2 * N0)) and U a uniform variate in (0, 1):

  m = mu * (ln(1/U))^2

This is the exact inverse of N(m)/N0 = exp(-sqrt(m/mu)) = U, so a caller can
sample fragment masses without inverting the count function.

Input:  [_casingMassKg, _fragmentCount, _uniform]
Output: sampled fragment mass (kg)
*/
params [
    ["_casingMassKg", 1, [0]],
    ["_fragmentCount", 1, [0]],
    ["_uniform", 0.5, [0]]
];

if (_casingMassKg <= 0 || _fragmentCount <= 0) exitWith { 0 };

private _u = (_uniform min 0.999999) max 0.000001;
private _mu = _casingMassKg / (2 * _fragmentCount);
private _t = ln (1 / _u);
_mu * _t * _t
