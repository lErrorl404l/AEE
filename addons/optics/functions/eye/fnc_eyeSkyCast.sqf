#include "..\..\script_component.hpp"

/*
Engine raycast for sky visibility.

Casts one ray per direction and reports whether the ray reached open sky
(true) or hit geometry (false). The driver passes the eye position, the sky
directions, the objects to ignore, and the ray range.

This is the only kernel in the eye module that touches the engine, so it is
source-contracted in the test suite and is not executed by sqf_lite. It
mirrors the shadow ray in addons/thermal/functions/surface/
fnc_isPositionShadowed.sqf (GEOM/NONE, nearest first, one result).

Arguments:
  0: Array - eye position, ASL
  1: Array - sky directions, unit vectors
  2: Array - objects to ignore (0, 1 or 2 elements)
  3: Number - ray range, m

Returns:
  Array - one boolean per direction; true when the ray reached open sky.
*/

params [
    ["_eye", [0, 0, 0], [[]]],
    ["_directions", [], [[]]],
    ["_objects", [], [[]]],
    ["_range", 100, [0]]
];

private _ignoreA = objNull;
private _ignoreB = objNull;
if ((count _objects) > 0) then { _ignoreA = _objects select 0; };
if ((count _objects) > 1) then { _ignoreB = _objects select 1; };

private _clear = [];
{
    private _end = _eye vectorAdd (_x vectorMultiply _range);
    private _hits = lineIntersectsSurfaces [_eye, _end, _ignoreA, _ignoreB, true, 1, "GEOM", "NONE"];
    _clear pushBack ((count _hits) == 0);
} forEach _directions;

_clear
