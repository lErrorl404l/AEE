#include "..\..\script_component.hpp"
/*
Deterministic eight-direction (D8) runoff routing (issue #24).

Runoff does not stay where it falls. Each cell of the terrain passes its
accumulated flow to the single neighbour of the eight with the steepest
downward slope. A cell with no lower neighbour is a sink and keeps its water.
The accumulated area at a cell is therefore the area that drains to it, which
is the catchment the river stage needs.

Source: O'Callaghan and Mark (1984), "The extraction of drainage networks
from digital elevation data", Computer Vision, Graphics and Image Processing
28:323-344.

The grid is IMPLICIT: it is fixed by an origin, a cell count and a cell size,
not stored as a map. Terrain heights are read once per cell with
getTerrainHeightASL, and the finished accumulation is cached, so a later call
with the same grid is a hash lookup and never re-probes the heightmap.

COST MODEL: a scan reads one height per cell. Stratis is 8 km square, so a
100 m step is about 6,700 cells; Altis is 30 km, so about 95,000. The scan
runs once per machine per mission and the result is cached under the grid
key. It is deterministic: a pure function of the terrain and the grid, so
every machine computes the same answer and no network publish is needed.
This is the mod's deterministic-state contract, not the server-only terrain
sweep: that sweep is an optimisation, and a JIP client must still reach the
same values.

TIE-BREAK: when two or more neighbours share the steepest slope, the first in
the fixed order below wins, because the comparison is strict (slope > best).
The order is E, SE, S, SW, W, NW, N, NE, clockwise from east. There is no
random choice, so the result is reproducible.

Args:
  0: grid origin [x, y] (ARRAY, metres, default [0, 0])
  1: cells along x (NUMBER, default 32)
  2: cells along y (NUMBER, default 32)
  3: cell size (NUMBER, metres, default 100)

Returns a flat array of length nx*ny, row-major (index = iy*nx + ix). Each
element is the contributing area in m2 for that cell.
*/

params [
    ["_origin", [0, 0], [[]]],
    ["_nx", 32, [0]],
    ["_ny", 32, [0]],
    ["_step", 100, [0]]
];

if (count _origin < 2) exitWith { [] };
if !(_nx isEqualType 0) then { _nx = 32; };
if !(_ny isEqualType 0) then { _ny = 32; };
if !(_step isEqualType 0) then { _step = 100; };
_nx = floor (_nx max 1);
_ny = floor (_ny max 1);
_step = _step max 1;

private _gridKey = format ["%1_%2_%3_%4_%5", _origin#0, _origin#1, _nx, _ny, _step];
private _cache = missionNamespace getVariable [QGVAR(d8AccumulationCache), createHashMap];
if (_gridKey in _cache) exitWith { _cache get _gridKey };

private _count = _nx * _ny;

// ─── 1. Sample the terrain, one read per cell ─────────────────────────────
private _heights = [];
private _ox = _origin#0;
private _oy = _origin#1;
private _ws = worldSize;
for "_iy" from 0 to (_ny - 1) do {
    for "_ix" from 0 to (_nx - 1) do {
        // The last row or column can fall just past the map when worldSize
        // is not a multiple of the step. Clamp to the map edge.
        private _px = (_ox + ((_ix + 0.5) * _step)) min _ws;
        private _py = (_oy + ((_iy + 0.5) * _step)) min _ws;
        _heights pushBack (getTerrainHeightASL [_px, _py, 0]);
    };
};

// ─── 2. Steepest-descent receiver for every cell ──────────────────────────
// The eight offsets in the fixed tie-break order. A diagonal step is
// sqrt(2) times an orthogonal one, so the slope is the drop over the true
// distance, not the drop alone.
private _neighbours = [[1, 0], [1, 1], [0, 1], [-1, 1], [-1, 0], [-1, -1], [0, -1], [1, -1]];
private _diag = _step * (sqrt 2);
private _receivers = [];
for "_iy" from 0 to (_ny - 1) do {
    for "_ix" from 0 to (_nx - 1) do {
        private _index = (_iy * _nx) + _ix;
        private _h = _heights select _index;
        private _best = -1;
        private _bestSlope = 0;
        {
            _x params ["_dx", "_dy"];
            private _jx = _ix + _dx;
            private _jy = _iy + _dy;
            if (_jx >= 0 && _jx < _nx && _jy >= 0 && _jy < _ny) then {
                private _dist = [_diag, _step] select ((_dx == 0) || (_dy == 0));
                private _slope = (_h - (_heights select ((_jy * _nx) + _jx))) / _dist;
                if (_slope > _bestSlope) then {
                    _bestSlope = _slope;
                    _best = (_jy * _nx) + _jx;
                };
            };
        } forEach _neighbours;
        _receivers pushBack _best;
    };
};

// ─── 3. Accumulate downhill ───────────────────────────────────────────────
// Every cell starts with its own area. Flow is strictly downhill, so a cell
// is always lower than everything that drains into it. Processing the cells
// in descending height order therefore visits every upstream contributor
// before the cell it feeds, in one pass.
private _cellArea = _step * _step;
private _area = [];
for "_i" from 0 to (_count - 1) do { _area pushBack _cellArea; };
private _order = [];
for "_i" from 0 to (_count - 1) do {
    _order pushBack [_heights select _i, _i];
};
_order sort false;   // descending height; the index breaks an equal-height tie
{
    private _receiver = _receivers select (_x#1);
    if (_receiver >= 0) then {
        _area set [_receiver, (_area select _receiver) + (_area select (_x#1))];
    };
} forEach _order;

_cache set [_gridKey, _area];
missionNamespace setVariable [QGVAR(d8AccumulationCache), _cache];

_area
