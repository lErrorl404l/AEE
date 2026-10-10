#include "..\script_component.hpp"
/*
Beer-Lambert transmission of each colour band through the water column
(issue #14).

The model is one exponential per band:

    T_band(z) = exp(-Kd_band * z)

T is the fraction of the surface light that reaches the depth.  Kd comes
from fnc_waterTypeKd or from a direct measurement.  The three bands (red
660 nm, green 530 nm, blue 475 nm) shift toward blue with depth because
Kd is larger for red.

Scope.  The model uses Kd (ambient diffuse attenuation), never the beam
attenuation c = a + b.  Kd is always smaller than c.  Kd is correct for
ambient visibility and colour.  c is correct only for a point light or a
discrete object.  The two are not modelled together.

Input:  [_depth, _kdR, _kdG, _kdB]
          _depth - depth in metres (0 = surface)
          _kdR   - red band attenuation, 660 nm (m^-1)
          _kdG   - green band attenuation, 530 nm (m^-1)
          _kdB   - blue band attenuation, 475 nm (m^-1)
Output: [T_R, T_G, T_B] - transmission fraction per band (0..1)
*/

params [
    ["_depth", 0, [0]],
    ["_kdR", 0, [0]],
    ["_kdG", 0, [0]],
    ["_kdB", 0, [0]]
];

private _d = 0 max _depth;

[
    exp (-_kdR * _d),
    exp (-_kdG * _d),
    exp (-_kdB * _d)
]
