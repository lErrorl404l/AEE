#include "..\script_component.hpp"

/*
Route exposure kernel (reusable AI substrate).

Pure: no missionNamespace, no GVAR or EGVAR, no engine command.

The exposure term of the data-driven pathfinder ("seeing blind").  A
destination inside the effective visibility range is observable, so it is
exposed.  The range is the repo's OWN visibility model output, not a second
model: the driver passes EGVAR(vision,viewDistanceTarget), which
fnc_calculateViewDistance derives from Koschmieder's law
(V = 3.912 / sigma_total, Koschmieder 1924) and the Johnson detection
criterion.  This kernel turns the range and the candidate-to-observer
distance into a 0..1 exposure fraction.

  exposure = 1 - clamp(distance / viewRange, 0, 1)

A candidate at the observer is fully exposed (1).  A candidate at or beyond
the visibility range is not observable (0).

The range is SOURCED (the repo's Koschmieder visibility model).  The linear
observable fraction is a modelling choice, UNSOURCED.

Arguments:
  0: Number - the candidate-to-observer distance, metres
  1: Number - the effective visibility range, metres

Returns:
  Number - the exposure, 0 to 1
*/

params [
    ["_distance", 0, [0]],
    ["_viewRange", 0, [0]]
];

if (_viewRange <= 0) exitWith { 0 };

private _fraction = (((_distance / _viewRange) max 0) min 1);

1 - _fraction
