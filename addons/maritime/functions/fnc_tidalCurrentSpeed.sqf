#include "..\script_component.hpp"

/*
Tidal current speed from the tidal height (progressive shallow-water wave).

For a progressive long wave in water of depth H the horizontal particle
velocity is in phase with the surface elevation eta and scales as:

  u = eta * sqrt(g / H)

eta is the tidal height the harmonic tide model publishes
(aee_core_currentTideOffset_m), H is the water depth, and g = 9.80665 m s^-2.
A 1 m tide in 10 m of water gives 0.99 m s^-1; in 50 m it gives 0.44 m s^-1
(the shallow-water result, Stewart 2008; Neill 2017 tidal-stream review).

Pure: no missionNamespace, no GVAR or EGVAR, no engine command.  The driver
FUNC(calculateOceanCurrent) reads the tide height and calls this kernel.

Arguments:
  0: Number - tidal height eta, m
  1: Number - water depth H, m (positive)

Returns:
  Number - tidal current speed |u|, m s^-1
*/

params [
    ["_tideHeight_m", 0, [0]],
    ["_depth_m", 10, [0]]
];

private _g = 9.80665;
private _H = _depth_m max 1;   // a depth of zero has no long-wave solution

(abs _tideHeight_m) * sqrt (_g / _H)
