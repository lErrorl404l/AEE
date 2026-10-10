#include "..\..\script_component.hpp"
/*
Radar cross section (RCS) by target class, m^2.

The table maps a target class token to a representative RCS (the
mid-point of the issue's range, in the optical region - the SHF vs
vehicle case).  It is the input to the radar range equation.

  class        RCS m^2
  stealth      0.00316   (0.001-0.01, mid)
  fighter      3         (1-6)
  bomber       55        (10-100)
  helicopter   3
  person       0.3       (0.1-1)
  vehicle      10        (5-20)
  ship         1000      (100-10000)
  boat         0.2       (0.02-2)

UNSOURCED.  The issue states these class ranges but the source it names
(Skolnik, "Radar Handbook", 3rd ed.) is NOT held locally, and no
catalogue under data/ holds an RCS figure.  Per the repository's
UNSOURCED marker rule the values are leads: they never fill a
runtime-required field and the grade is "claimed".  A held source must
replace them before this model is trusted for any decision.

The Rayleigh region (lambda^-4) does NOT apply here: at SHF (3-30 cm)
against these vehicle and aircraft classes the target is in the optical
region, so a flat RCS is correct (the issue's own correction).

Pure: reads no engine state, writes none.

Arguments:
  0: String - target class token

Returns:
  Number - representative RCS sigma, m^2 (0 when the class is unknown)
*/
params [
    ["_class", "", [""]]
];

private _key = toLower _class;

private _table = [
    ["stealth", 0.00316],
    ["fighter", 3],
    ["bomber", 55],
    ["helicopter", 3],
    ["person", 0.3],
    ["vehicle", 10],
    ["ship", 1000],
    ["boat", 0.2]
];

private _sigma = 0;
{
    if ((_x select 0) == _key) then {
        _sigma = _x select 1;
    };
} forEach _table;

_sigma
