#include "..\script_component.hpp"
/*
Transmission loss in the sea (issue #113).

Urick, "Principles of Underwater Sound", 3rd ed., McGraw-Hill 1983,
ISBN 0-07-066087-5, ch. 5-6.  Corroborated by the US Naval Academy ES310
sonar-propagation notes.

Transmission loss is spreading plus absorption:

    spherical:   TL = 20 log10(r) + alpha * r
    cylindrical: TL = 10 log10(r) + alpha * r

  r      range, m
  alpha  absorption, dB/km (from fnc_calculateAbsorptionWater)
  TL     transmission loss, dB

The 20 log10 form is spherical spreading (open water, a point source).
The 10 log10 form is cylindrical spreading, which holds near the surface
or in a sound channel where the energy is trapped in a duct and spreads
in two dimensions.  Spherical is the default.

Absorption enters as dB/km times the range in km, so r/1000.  The reference
is 1 m: TL is zero at r = 1 m for spherical spreading.

Input:  [range_m, alpha_dB_per_km, spreading]
          spreading - "spherical" (default) or "cylindrical"
Output: transmission loss in dB
*/

params [
    ["_rangeM", 1, [0]],
    ["_alphaDbKm", 0, [0]],
    ["_spreading", "spherical", [""]]
];

private _r = 1 max _rangeM;
private _logFactor = [20, 10] select (_spreading == "cylindrical");

(_logFactor * (log _r)) + (_alphaDbKm * (_r / 1000))
