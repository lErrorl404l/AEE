#include "..\..\script_component.hpp"

/*
Dense-gas gravity slumping (issue #120).

A gas heavier than air slumps outward under its own weight.  The
DEGADIS User's Manual (Havens & Spicer 1985, USCG-D-24-85, DTIC
ADA171524) gives the frontal (gravity-spreading) velocity, Eq 1-1:

  u_f = C_e * sqrt(g * A' * H)        A' = (rho - rho_a) / rho_a

with C_e = 1.15.  The front coefficient comes from the dense-gas
slumping experiments (Schmidt 1911; Benjamin 1968; Fannelop et al. 1980;
Huppert & Simpson 1980).  A' is the reduced-density ratio; the issue's
"reduced gravity" g' = g * A'.

The bulk release Richardson number measures buoyancy against the wind
(DEGADIS Vol I, after van Ulden 1974):

  Ri* = g * A' * H / u^2

A high Ri* means the cloud slumps against the wind; a low Ri* means the
wind carries it and it behaves as a passive plume.  The regime cut
points (30 and 1) the issue states are NOT in DEGADIS and are therefore
not applied here; the raw Ri* is returned.

The frontal entrainment velocity follows DEGADIS Eq II-12, u_e = e*u_f,
with e the frontal entrainment coefficient.  DEGADIS's shipped default
is e = 0.59 (Vol III listing, "epsilon ... USED IN AIR ENTRAINMENT
SPECIFICATION"); the report text quotes 0.60.  This kernel uses the
shipped default 0.59.

Pure: no missionNamespace, no GVAR or EGVAR, no engine command.

Arguments:
  0: NUMBER - density ratio rho_g/rho_a (1 = neutral)
  1: NUMBER - cloud height H, m
  2: NUMBER - wind speed u, m/s

Returns:
  ARRAY [reducedGravity m/s2, frontalVelocity m/s, richardson,
         entrainmentVelocity m/s, denseActive BOOL]
*/

params [
    ["_densityRatio", 1, [0]],
    ["_cloudHeight", 1, [0]],
    ["_windSpeed", 0, [0]]
];

private _g = 9.80665;
private _h = _cloudHeight max 0;
private _buoyancy = _densityRatio - 1;

private _gPrime = _g * _buoyancy;

// A gas lighter than air (buoyancy < 0) does not slump; the square root
// would be undefined.  Only a heavier-than-air gas has a frontal velocity.
private _frontal = 0;
if (_buoyancy > 0) then {
    _frontal = 1.15 * sqrt (_g * _buoyancy * _h);
};

private _richardson = 0;
if (_windSpeed > 0.01) then {
    _richardson = _g * _buoyancy * _h / (_windSpeed ^ 2);
};

private _entrainment = 0.59 * _frontal;

[_gPrime, _frontal, _richardson, _entrainment, _buoyancy > 0]
