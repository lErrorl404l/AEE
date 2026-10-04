#include "..\script_component.hpp"

/*
Spook-range kernel (wildlife ecology).

Pure: no missionNamespace, no GVAR or EGVAR, no engine command.  The
flight-initiation distance of a spooked animal for a stimulus magnitude.
The base range is the caller's per-species value.  Every constant is the
caller's, so no policy lives here.

Arguments:
  0: Number - the stimulus magnitude, 0 to 1
  1: Number - the per-species sensitivity multiplier
  2: Number - the per-species base range, metres

Returns:
  Number - the spook range in metres, 0 or more
*/

params [
    ["_magnitude", 0, [0]],
    ["_sensitivity", 1, [0]],
    ["_baseRange", 20, [0]]
];

private _mag = ((_magnitude max 0) min 1);
private _sensitivityClamped = (_sensitivity max 0);
private _range = _baseRange * (0.5 + _mag) * _sensitivityClamped;

((_range max 0) min 1e6)
