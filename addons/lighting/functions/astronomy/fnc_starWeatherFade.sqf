#include "..\..\script_component.hpp"

/*
Star cloud fade.

The sky glow, the moon and light pollution already set which stars are
visible at all through the limiting magnitude (fnc_calculateLimitingMagnitude,
Schaefer 1990; Albers & Duriscoe 2001).  What remains for a visible star is
whether cloud stands in the line of sight: the engine overcast is the cloud
fraction, so a random line of sight is clear with probability 1 - overcast,
and the render scale is the value times that clear-sky fraction.  Fog is
ground fog, below the line to a star, so it does not enter.

Arguments:
  0: Number - value to fade
  1: Number - engine overcast (cloud fraction), 0..1
  2: Number - engine fog, 0..1 (unused, see above)

Returns:
  Number - faded value in 0..value
*/

params [
    ["_value", 0, [0]],
    ["_overcast", 0, [0]],
    ["_fog", 0, [0]]
];

_value * (1 - ((_overcast max 0) min 1))
