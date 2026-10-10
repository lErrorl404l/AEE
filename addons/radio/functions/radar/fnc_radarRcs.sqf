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

UNSOURCED.  The issue states these class ranges but names the wrong
source.  A source check found the canonical figures in Skolnik,
"Introduction to Radar Systems", Table 2.2 (man 1, bird 0.01,
automobile 100, pickup truck 200, large fighter 6, large bomber 40,
jumbo jet 100, small open boat 0.02) - NOT the "Radar Handbook" the
issue cites.  Against that table the issue's "vehicle 5-20 m^2"
CONFLICTS (the canonical vehicle is ~100-200 m^2), and the stealth
(0.001-0.01) and helicopter (~3) rows do not appear at all.  No
catalogue under data/ holds an RCS figure, and the source is not held
locally.

Per the repository's UNSOURCED marker rule the values are leads: they
never fill a runtime-required field and the grade is "claimed".  A held
source must replace them before this model is trusted for any decision.

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
