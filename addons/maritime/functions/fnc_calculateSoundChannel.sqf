#include "..\script_component.hpp"
/*
The deep sound channel (SOFAR) axis (issue #113).

The speed of sound in the sea has a vertical minimum.  Above it the
temperature falls with depth, so sound speed falls (the thermocline).
Below it the water is isothermal and pressure raises the sound speed.  The
minimum traps sound: rays bend toward the slow water on both sides and
oscillate about the axis, so a signal can travel thousands of kilometres.
This is the SOFAR channel (sound fixing and ranging), described
independently by Ewing and Worzel and by Brekhovskikh; the channel axis at
mid-latitudes is near 1000 m (indicative, Wenz and Urick; the exact depth
follows the local profile, not a fixed constant).

This kernel finds the axis from a sound-speed profile: the shallowest depth
at or below the source where the sound speed is least.  The profile comes
from fnc_calculateSoundSpeedProfile.

Input:  [profile, sourceDepth]
          profile     array of [depth, c] pairs, sorted by depth
          sourceDepth m (the axis is searched at or below this depth)
Output: [axisDepth, axisSpeed].  [0, 0] for an empty profile.
*/

params [
    ["_profile", [], [[]]],
    ["_sourceDepth", 0, [0]]
];

private _n = count _profile;
if (_n < 1) exitWith { [0, 0] };

private _axisDepth = (_profile select 0) select 0;
private _axisSpeed = (_profile select 0) select 1;

{
    private _z = _x select 0;
    private _c = _x select 1;
    if (_z >= _sourceDepth && _c < _axisSpeed) then {
        _axisSpeed = _c;
        _axisDepth = _z;
    };
} forEach _profile;

[_axisDepth, _axisSpeed]
