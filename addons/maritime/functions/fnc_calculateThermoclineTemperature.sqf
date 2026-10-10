#include "..\script_component.hpp"
/*
Thermocline temperature profile (issue #17).

The temperature falls from the mixed-layer (surface) value to the deep value
across the thermocline.  The profile is a hyperbolic tangent in depth:

    T(z) = T_deep + (T_surf - T_deep) * (1 - tanh((z - z_tc) / w)) / 2

  z      depth (m, positive down, 0 = surface)
  z_tc   thermocline centre depth (m)
  w      thermocline half-width scale (m)
  T_surf mixed-layer (surface) temperature (degC)
  T_deep deep-water temperature (degC)

At z = z_tc the temperature is the midpoint (T_surf + T_deep)/2.  Well above
the thermocline it is T_surf.  Well below it is T_deep.  A smaller w is a
sharper thermocline.

SQF has no tanh command, so tanh is built from exp:

    tanh(x) = 1 - 2 / (exp(2x) + 1)

which is the exact identity, not an approximation.  The exp overflows to
infinity for a very large positive x, and then the expression saturates to
1 without error; for a very large negative x, exp underflows to 0 and the
expression saturates to -1.

Source: the tanh form is the standard analytical representation of a
monotonic thermocline, and issue #17 prescribes it.  It is a modelling
choice, not a single published constant.  The depth and width ranges come
from the observed seasonal thermocline: 20 to 100 m depth with the sharp
gradient over tens of metres (Stewart 2008, section 6.5).

Input:  [_depth, _tempSurface, _tempDeep, _zThermocline, _width]
Output: temperature at the depth (degC)
*/

params [
    ["_depth", 0, [0]],
    ["_tempSurface", 15, [0]],
    ["_tempDeep", 4, [0]],
    ["_zThermocline", 50, [0]],
    ["_width", 30, [0]]
];

private _w = _width max 0.001;
private _x = (_depth - _zThermocline) / _w;
private _tanh = 1 - 2 / (exp (2 * _x) + 1);

_tempDeep + (_tempSurface - _tempDeep) * (1 - _tanh) / 2
