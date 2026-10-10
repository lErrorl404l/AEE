#include "..\..\script_component.hpp"

/*
Scene luminance from the ambient and local terms.

The ambient (sky) term reaches the eye only through the fraction of open sky
above the observer. A local light does not: a torch lights the scene in a
closed room, so the local term is added in full and is not scaled by sky
visibility.

Arguments:
  0: Number - ambient (sky) illuminance, lx
  1: Number - local (point and beam) illuminance, lx
  2: Number - sky fraction in [0, 1]

Returns:
  Number - total scene illuminance, lx.
*/

params [
    ["_ambientLux", 0, [0]],
    ["_localLux", 0, [0]],
    ["_skyFraction", 0, [0]]
];

(_ambientLux * _skyFraction) + _localLux
