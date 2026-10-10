#include "..\..\script_component.hpp"

/*
Fragment velocity decay with range (DDESB TP-12).

A fragment loses speed to aerodynamic drag.  The TP-12 model is an exponential
decay with a fragment-mass-dependent length scale L:

  V(R) = V0 * exp(-R / L)
  L    = 247 * m^(1/3)      (m in kg)

The length scale is derived from a fragment density of 2.6 g/cm3 and a drag
coefficient of 1.28.  V0 is the launch (Gurney) velocity.  At V0 = 1200 m/s a
0.1 g fragment gives 502 / 88 / 15 m/s at 10 / 30 / 50 m, and a 10 g fragment
gives 995 / 683 / 469 m/s.

Input:  [_muzzleVelocity, _fragmentMassKg, _rangeM]
Output: fragment velocity at range (m/s)
*/
params [
    ["_muzzleVelocity", 1200, [0]],
    ["_fragmentMassKg", 0.0001, [0]],
    ["_rangeM", 10, [0]]
];

if (_muzzleVelocity <= 0 || _fragmentMassKg <= 0 || _rangeM < 0) exitWith { 0 };

private _l = 247 * (_fragmentMassKg ^ (1 / 3));
_muzzleVelocity * exp (-(_rangeM / _l))
