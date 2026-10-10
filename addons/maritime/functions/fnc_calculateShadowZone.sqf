#include "..\script_component.hpp"
/*
The shadow zone below the thermocline (issue #113).

Urick, "Principles of Underwater Sound", 3rd ed., McGraw-Hill 1983,
ISBN 0-07-066087-5, ch. 6.  Corroborated by the US Naval Academy ES310
sonar-propagation notes.

In a summer profile the temperature falls through the thermocline, so the
sound speed falls with depth (a negative gradient).  A ray bends toward the
slower sound speed, so a ray from a shallow source bends downward and
refracts away from the deep layer.  Below the sound-channel axis a deep
receiver is reached by no direct ray: this is the shadow zone, a favoured
depth for a submarine.

This kernel reports the direct-path shadow as a depth band.  The top is the
sound-channel axis (the base of the thermocline, from
fnc_calculateSoundChannel); the bottom is the base of the profile.  The
region below the axis is where the direct rays from a shallow source have
all bent away.

Ceiling.  The range-dependent boundary (the first convergence zone, which
refills the shadow beyond 20-30 nautical miles) is NOT modelled.  Urick
gives the convergence-zone geometry; the quantitative "best depth" rule is
not a closed form and is not reproduced here.  The band below the axis is
the honest direct-path answer within the engine scope.

A source at or below the axis casts no shadow below itself in this model:
the search for the axis is at or below the source, so a deep source returns
an empty band.

Input:  [profile, sourceDepth]
          profile     array of [depth, c] pairs, sorted by depth
          sourceDepth m
Output: [shadowTop, shadowBottom].  [0, 0] when there is no shadow zone.
*/

params [
    ["_profile", [], [[]]],
    ["_sourceDepth", 0, [0]]
];

private _n = count _profile;
if (_n < 2) exitWith { [0, 0] };

private _bottom = (_profile select (_n - 1)) select 0;

// The sound-channel axis below the source: the least sound speed.
private _axisDepth = _bottom;
private _axisSpeed = 1e9;
{
    private _z = _x select 0;
    private _c = _x select 1;
    if (_z >= _sourceDepth && _c < _axisSpeed) then {
        _axisSpeed = _c;
        _axisDepth = _z;
    };
} forEach _profile;

// No axis strictly below the source: a deep source has no shadow below it.
if (_axisDepth >= _bottom) exitWith { [0, 0] };

[_axisDepth, _bottom]
