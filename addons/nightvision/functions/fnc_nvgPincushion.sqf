#include "..\script_component.hpp"

/*
Single edge scale for the RadialBlur vignette.

Arma exposes no radial pincushion parameter, so the edge read is a blur
approximation.  The per-tier edge factors are the values already in the
parent's inline erosion switch.  The true warp percent per generation is
UNSOURCED.

This returns ONE multiplier, applied exactly once by the parent.  The result
is clamped so the final RadialBlur power stays at or below the parent's 0.01
guard.

Arguments:
  0: Number - tier index (0 GEN1 .. 3 PVS31)
  1: Number - vignette power x (the parent's _vigStrength select 0)
  2: Number - strength in [0, 1]

Returns:
  Number - edge multiplier.
*/

params [
    ["_tierIdx", 0, [0]],
    ["_vigPowerX", 0.004, [0]],
    ["_strength", 0.5, [0]]
];

private _edge = [2.5, 1.3, 1.0, 1.0] select ((_tierIdx max 0) min 3);
private _scale = 1 + (_edge - 1) * ((_strength max 0) min 1);

_scale min (0.01 / (_vigPowerX max 0.0001))
