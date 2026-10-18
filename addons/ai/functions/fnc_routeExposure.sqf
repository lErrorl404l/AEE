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
criterion.  The exposure is the apparent contrast of the candidate above the
2 percent contrast threshold that defines that range: Koschmieder's
attenuation C = C0 exp(-sigma d) with sigma = 3.912 / V, so

  exposure = (exp(-3.912 d / V) - 0.02) / (1 - 0.02), clamped to 0..1

A candidate at the observer is fully exposed (1).  A candidate at or beyond
the visibility range is at the threshold and not observable (0).

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

private _contrast = exp (-3.912 * ((_distance max 0) / _viewRange));

(((_contrast - 0.02) / 0.98) max 0) min 1
