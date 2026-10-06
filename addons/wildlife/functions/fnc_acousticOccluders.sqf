#include "..\script_component.hpp"

/*
Acoustic occluder collector (wildlife ecology).

Client-local wiring, not a pure kernel: it queries the engine for the
terrain objects near the listener and returns their positions, so
fnc_acousticLevel can do the line-of-sight geometry.  The query is bounded by
the radius and the cap, so the cost stays flat.

Arguments:
  0: Array  - the listener position, ASL
  1: Number - the query radius, metres
  2: Number - the object cap

Returns:
  Array - occluder positions, ASL, at most the cap
*/

params [
    ["_position", [0, 0, 0], [[]]],
    ["_radius", 60, [0]],
    ["_cap", 16, [0]]
];

private _objects = nearestTerrainObjects [
    _position,
    ["TREE", "SMALL TREE", "BUSH", "BUILDING", "WALL", "FENCE", "HOUSE"],
    _radius,
    false,
    true
];

private _out = [];
for "_i" from 0 to ((count _objects) - 1) do {
    if ((count _out) < _cap) then {
        private _object = _objects select _i;
        if (!isNull _object) then {
            _out pushBack getPosASL _object;
        };
    };
};

_out
