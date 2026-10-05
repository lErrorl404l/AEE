#include "..\..\script_component.hpp"

/*
Rain-scaled film grain parameters (aee-workshop-copy item 5).

Re-derived from fn_nightTime.sqf in Real Lighting and Weather (Workshop
2809399991).  The mod publishes no licence, so this is a re-derived numeric
kernel, not copied code.  No mod content is copied.

The source selected a six-element FilmGrain array from rain and sunOrMoon.
It wrote the literal `true` as the sixth element in three of the four
branches.  `true` is not a valid number for a post-process parameter, so AEE
writes 1 instead.  In Arma 3 the FilmGrain monochromatic parameter is 0 for
monochrome and any other value for colour (BIKI Post Process Effects, capture
20240220225631).  The last element is therefore ALWAYS 1 (colour), so the
grain never drains the scene to grey.  This is the same invariant the acuity
pass and the NVG tube model carry.

Branches (sunOrMoon < 0.5 is night):
  night and rain > 0.4 : [0.01, 0.7, 3.5, 1, 1, 1]
  night otherwise      : [0.01, 0.5, 0.5, 0.1, 0.1, 1]
  day and rain > 0.2   : [0.01, linearConversion [0.2, 1, rain, 0.7, 0.2, true], 3, 1, 1, 1]
  day otherwise        : [0.1, 0.5, 0.5, 0.1, 0.1, 1]

The kernel is pure: no missionNamespace, no GVAR or EGVAR, no engine state.
It reads only its arguments.

Arguments:
  0: Number - rain, 0 to 1 (engine rain)
  1: Number - sunOrMoon, 1 day and 0 night (engine sunOrMoon)

Returns:
  Array - six FilmGrain parameters [intensity, sharpness, size, x, y, monochrome]
*/

params [
    ["_rain", 0, [0]],
    ["_sunOrMoon", 1, [0]]
];

private _params = [0.1, 0.5, 0.5, 0.1, 0.1, 1];

if (_sunOrMoon < 0.5) then {
    if (_rain > 0.4) then {
        _params = [0.01, 0.7, 3.5, 1, 1, 1];
    } else {
        _params = [0.01, 0.5, 0.5, 0.1, 0.1, 1];
    };
} else {
    if (_rain > 0.2) then {
        _params = [0.01, linearConversion [0.2, 1, _rain, 0.7, 0.2, true], 3, 1, 1, 1];
    } else {
        _params = [0.1, 0.5, 0.5, 0.1, 0.1, 1];
    };
};

_params
