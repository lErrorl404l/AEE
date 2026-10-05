#include "..\..\script_component.hpp"

/*
Heat-haze sprite size (aee-workshop-copy item 7, part 1).

Re-derived from Better Visuals (Workshop 3351805137) fn_heatHaze.sqf, where
the sprite size is random [0.5, 1, 1.5].  The mod publishes no licence, so
this is a re-derived numeric kernel, not copied code.  No mod content is copied.
The caller supplies the random draw, so the kernel stays pure and testable.

The kernel is pure: no missionNamespace, no GVAR or EGVAR, no engine command.

Arguments:
  0: Number - random draw, expected 0..1

Returns:
  Number - 0.5 + draw, clamped 0.5..1.5
*/

params [["_rng", 1, [0]]];

private _value = 0.5 + _rng;
(_value max 0.5) min 1.5
