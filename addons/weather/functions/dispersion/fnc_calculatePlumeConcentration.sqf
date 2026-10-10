#include "..\..\script_component.hpp"

/*
Steady Gaussian plume concentration at a receptor.

Source: Turner, "Workbook of Atmospheric Dispersion Estimates", EPA AP-26
(1970), eq. 3.3 (the standard Gaussian plume with ground reflection):

  C = Q/(2 pi U sigma_y sigma_z)
      * exp(-y^2 / (2 sigma_y^2))
      * [ exp(-(z-H)^2 / (2 sigma_z^2)) + exp(-(z+H)^2 / (2 sigma_z^2)) ]

At ground level on the centreline (y=0, z=0) the bracket is 2, giving
C = Q/(pi U sigma_y sigma_z); for a ground source (H=0) this is the
C = Q/(pi U sigma_y sigma_z) form.  Q is the emission rate (mg/s), U the
wind (m/s), H the effective release height (m).

Arguments:
  0: emission rate Q (NUMBER, mg/s)
  1: wind speed U (NUMBER, m/s)
  2: sigma_y (NUMBER, m)
  3: sigma_z (NUMBER, m)
  4: effective height H (NUMBER, m)
  5: crosswind distance y (NUMBER, m)
  6: receptor height z (NUMBER, m)

Returns the concentration (mg/m3).
*/

params [
    ["_q", 0, [0]],
    ["_u", 1, [0]],
    ["_sigmaY", 1, [0]],
    ["_sigmaZ", 1, [0]],
    ["_h", 0, [0]],
    ["_y", 0, [0]],
    ["_z", 0, [0]]
];

// A minimum wind keeps the steady-source solution finite (calm air is
// handled by the puff path).
private _wind = _u max 0.1;
private _sy2 = 2 * _sigmaY * _sigmaY;
private _sz2 = 2 * _sigmaZ * _sigmaZ;

private _cross = exp (-(_y * _y) / _sy2);
private _up = exp (-((_z - _h) * (_z - _h)) / _sz2);
private _down = exp (-((_z + _h) * (_z + _h)) / _sz2);

private _c = (_q / (2 * pi * _wind * _sigmaY * _sigmaZ)) * _cross * (_up + _down);

_c
