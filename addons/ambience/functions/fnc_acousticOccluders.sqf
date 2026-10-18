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
  Array - barriers [x, y, topASL, halfWidth], at most the cap
*/

params [
    ["_position", [0, 0, 0], [[]]],
    ["_radius", 60, [0]],
    ["_cap", 16, [0]]
];

private _objects = nearestTerrainObjects [
    _position,
    ["BUILDING", "WALL", "FENCE", "HOUSE"],
    _radius,
    false,
    true
];

private _out = [];
for "_i" from 0 to ((count _objects) - 1) do {
    if ((count _out) < _cap) then {
        private _object = _objects select _i;
        if (!isNull _object) then {
            private _box = boundingBoxReal _object;
            private _lo = _box select 0;
            private _hi = _box select 1;
            private _pos = _object modelToWorldWorld [0, 0, _hi select 2];
            private _half = (((_hi select 0) - (_lo select 0)) max ((_hi select 1) - (_lo select 1))) / 2;
            _out pushBack [_pos select 0, _pos select 1, _pos select 2, _half];
        };
    };
};

_out
