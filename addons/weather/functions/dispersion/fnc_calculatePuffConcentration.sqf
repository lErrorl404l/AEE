#include "..\..\script_component.hpp"

/*
Gaussian puff concentration at a receptor.

Source: Turner, "Workbook of Atmospheric Dispersion Estimates", EPA AP-26
(1970), the instantaneous (puff) solution:

  C = M/((2 pi)^1.5 sigma_x sigma_y sigma_z)
      * exp(-(x-xc)^2 / (2 sigma_x^2))
      * exp(-(y-yc)^2 / (2 sigma_y^2))

M is the released mass (mg).  The puff centre is advected with the wind;
the caller passes the centre-to-receptor offsets.  sigma_x = sigma_y for
the puff (Briggs), evaluated at the travelled distance x = U t.

Arguments:
  0: released mass M (NUMBER, mg)
  1: sigma_x (NUMBER, m)
  2: sigma_y (NUMBER, m)
  3: sigma_z (NUMBER, m)
  4: downwind offset dx = x - xc (NUMBER, m)
  5: crosswind offset dy = y - yc (NUMBER, m)

Returns the concentration (mg/m3).
*/

params [
    ["_mass", 0, [0]],
    ["_sigmaX", 1, [0]],
    ["_sigmaY", 1, [0]],
    ["_sigmaZ", 1, [0]],
    ["_dx", 0, [0]],
    ["_dy", 0, [0]]
];

private _norm = _mass / ((2 * pi) ^ 1.5 * _sigmaX * _sigmaY * _sigmaZ);
private _ex = exp (-(_dx * _dx) / (2 * _sigmaX * _sigmaX));
private _ey = exp (-(_dy * _dy) / (2 * _sigmaY * _sigmaY));

_norm * _ex * _ey
