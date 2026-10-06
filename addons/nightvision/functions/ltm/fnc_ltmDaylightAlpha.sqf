#include "..\..\script_component.hpp"

/*
Laser target marker daylight alpha (aee-workshop-copy item 8).

Re-derived from fn_laser.sqf in Enhanced Visuals (Workshop 880703327).  The
mod publishes no licence, so this is a re-derived formula, not copied code.
No mod content is copied.

The source fades the IR laser marker in daylight.  AEE uses the engine
sunOrMoon factor (1 day, 0 night) and the formula alpha = 1.2 - sunOrMoon
clamped to 0..1.  At sunOrMoon 0 the alpha is 1, at sunOrMoon 1 the alpha is
0.2.  Only the marker alpha changes; the caller keeps the drawLine3D colour
hue.

The kernel is pure: no missionNamespace, no GVAR or EGVAR, no engine state.
It reads only its argument.

Arguments:
  0: Number - engine sunOrMoon, 1 day and 0 night

Returns:
  Number - marker alpha, 0 to 1
*/

params [
    ["_sunOrMoon", 1, [0]]
];

((1.2 - _sunOrMoon) max 0) min 1
