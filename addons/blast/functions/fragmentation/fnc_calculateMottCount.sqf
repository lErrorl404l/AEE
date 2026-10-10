#include "..\..\script_component.hpp"

/*
Mott fragment-size distribution, cumulative form (Mott 1943, 1947).

Mott's statistical theory of casing break-up gives the number of fragments
heavier than mass m:

  N(m) = N0 * exp(-sqrt(m / mu))

N0 is the total fragment count.  mu is the Mott parameter, half the mean
fragment mass:

  mu = M_casing / (2 * N0)

Input:  [_casingMassKg, _fragmentCount, _massKg]
Output: number of fragments heavier than _massKg
*/
params [
    ["_casingMassKg", 1, [0]],
    ["_fragmentCount", 1, [0]],
    ["_massKg", 0.001, [0]]
];

if (_casingMassKg <= 0 || _fragmentCount <= 0 || _massKg <= 0) exitWith { 0 };

private _mu = _casingMassKg / (2 * _fragmentCount);
_fragmentCount * exp (-(sqrt (_massKg / _mu)))
