#include "..\..\script_component.hpp"
/*
Distance to the nearest water, cached per grid cell (issue #24).

The tidal reach needs to know how far inland a position sits: a river
mouth rises with the tide and a reach 5 km upstream does not. The first
implementation probed the terrain every tick, up to 200 surfaceIsWater
calls per position per tick, on EVERY machine. That is the wrong cost
model for a mod built for large milsim sessions, where the environment
tick runs on every client.

Terrain facts are map properties. The mod already scans them once at
mission start (fnc_scanTerrainSignals) and caches the result, and this
follows that pattern: the first query for a cell walks outward and caches
the answer, so the walk happens once per cell rather than every tick.

The result is a pure function of position and the terrain, so every
machine computes the same distance and the state stays deterministic with
no network traffic.

Args:
  0: position (ARRAY, [x, y], default [0, 0])
  1: search limit (NUMBER, metres, default 5000)

Returns the distance to the nearest water in metres, capped at the limit.
*/

params [["_pos", [0, 0], [[]]], ["_limit", 5000, [0]]];

if (count _pos < 2) exitWith { _limit };
if !(_limit isEqualType 0) then { _limit = 5000; };
if (_limit <= 0) exitWith { 0 };

// 100 m cell, matching its own rounding. The grid is coarse on purpose:
// the tide falls to zero over kilometres, so a cell boundary cannot move
// the answer more than the model's own resolution.
private _cx = floor ((_pos select 0) / 100);
private _cy = floor ((_pos select 1) / 100);
private _key = format ["%1_%2", _cx, _cy];

private _cache = missionNamespace getVariable [QGVAR(coastDistanceCache), createHashMap];
if (_key in _cache) exitWith { _cache get _key };

// Walk outward in 100 m rings. Eight bearings are enough at this scale:
// the model interpolates linearly to zero over kilometres, so a bearing
// that misses a narrow inlet changes the distance by one ring at most.
private _step = 100;
private _dist = _limit;
private _found = false;
private _ox = _cx * 100;
private _oy = _cy * 100;
for "_d" from _step to _limit step _step do {
    {
        private _probe = [
            _ox + (_d * sin _x),
            _oy + (_d * cos _x)
        ];
        if (surfaceIsWater _probe) then {
            _dist = _d;
            _found = true;
        };
    } forEach [0, 45, 90, 135, 180, 225, 270, 315];
    if (_found) exitWith {};
};

_cache set [_key, _dist];
missionNamespace setVariable [QGVAR(coastDistanceCache), _cache];

_dist
