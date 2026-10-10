#include "..\script_component.hpp"
/*
Two-layer (interfacial) internal-wave phase speed (issue #17).

In a two-layer ocean (a warm upper layer over a cold lower layer) the
density difference supports an internal wave on the interface.  For a long
wave (wavelength much greater than the layer thickness) the phase speed is:

    g' = g * (rho2 - rho1) / rho2          reduced gravity
    c  = sqrt( g' * h1 * h2 / (h1 + h2) )   two-layer phase speed

  g    gravitational acceleration (m/s2)
  rho1 upper-layer density (kg/m3), rho2 lower-layer density (kg/m3)
  h1   upper-layer thickness (m), h2 lower-layer thickness (m)

Because the density difference is small (d(rho)/rho about 0.001 to 0.003)
the reduced gravity is two to three orders of magnitude below g, and the
internal wave is far slower than a surface wave.

Limits from the same expression: when h2 is much greater than h1 the speed
tends to sqrt(g' * h1), the wave runs on the upper layer alone; when
h1 = h2 = D/2 the speed tends to sqrt(g' * D / 4).

The reduced gravity uses the Boussinesq form with the reference density
taken as the lower layer.  The exact symmetric two-layer form is
g' = g * (rho2 - rho1) / (rho2 + rho1).  The two differ by about 0.1
percent for seawater, so either is acceptable; this one is stated.

When the lower layer is not denser than the upper layer (rho2 <= rho1) the
column is unstable and there is no internal wave, so the speed is 0.

Sources:
  Gill (1982) Atmosphere-Ocean Dynamics, Academic Press, section 6.2
    (two-layer internal waves; the phase speed and the reduced gravity).
  Turner (1973) Buoyancy Effects in Fluids, Cambridge University Press,
    section 2.1 (interfacial waves).
  Phillips (1977) The Dynamics of the Upper Ocean, Cambridge University
    Press, page 37 (the symmetric reduced gravity and the deep-water
    dispersion).
  WHOI 12.800, chapter 11 "Internal Waves" (the two-layer result).

Input:  [_rho1, _rho2, _h1, _h2, _g]
Output: [c, gPrime] - phase speed (m/s), reduced gravity (m/s2)
*/

params [
    ["_rho1", 1025, [0]],
    ["_rho2", 1027.8, [0]],
    ["_h1", 50, [0]],
    ["_h2", 1000, [0]],
    ["_g", 9.80665, [0]]
];

private _gPrime = _g * (_rho2 - _rho1) / _rho2;
private _c = 0;
if (_gPrime > 0) then {
    _c = sqrt (_gPrime * _h1 * _h2 / (_h1 + _h2));
};

[_c, _gPrime]
