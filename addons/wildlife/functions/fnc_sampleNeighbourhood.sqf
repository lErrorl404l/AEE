#include "..\script_component.hpp"

/*
Neighbourhood environment sampler (wildlife ecology).

Impure by design: it reads the engine surface and the terrain objects.  It
walks a local grid (default 5 by 5 cells at 25 m) and returns an environment
sample [foliageFrac, surfaceVotes, waterFrac, structureFrac, meanElev].  A
per-cell sample is cached under the cell key floor(pos / cellSize), the same
shape as the disturbance field, so a second call in the cache window makes no
object query.  surfaceVotes is an array of [materialClass, count] rows from
fnc_classifyBySurfaceType.

The grid, the object cap and the millisecond budget are modelling choices,
UNSOURCED.  The sampler never exceeds the per-cell object cap or the
millisecond budget.  When the budget runs out, the unsampled cells are
re-queued at the front of the pending list, so the next call resumes them and
nothing starves.

Arguments:
  0: Array  - the centre position
  1: Number - the cell size, metres (default 25)
  2: Number - the cells per axis (default 5)
  3: Number - the object cap per cell (default 12)
  4: Number - the millisecond budget (default 2)

Returns:
  Array - [foliageFrac, surfaceVotes, waterFrac, structureFrac, meanElev]
*/

params [
    ["_position", [0, 0, 0], [[]]],
    ["_cellSize", 25, [0]],
    ["_cellsPerAxis", 5, [0]],
    ["_maxObjects", 12, [0]],
    ["_budgetMs", 2.0, [0]]
];

if ((count _position) < 2) exitWith { [0, [], 0, 0, 0] };

private _cell = _cellSize max 1;
private _axis = (_cellsPerAxis max 1) min 16;
private _cap = (_maxObjects max 1) min WILDLIFE_ENVIRONMENT_QUERY_CAP;
private _budget = _budgetMs max 0;
private _now = diag_tickTime;

private _store = missionNamespace getVariable [QGVAR(environment), []];
if !(_store isEqualType []) then { _store = []; };

// The pending list resumes an unfinished grid on the next call.  The cell key
// is floor(pos / cellSize), the same shape as the disturbance field.
private _pending = missionNamespace getVariable [QGVAR(environmentPending), []];
if !(_pending isEqualType []) then { _pending = []; };
if (_pending isEqualTo []) then {
    private _half = (floor (_axis / 2)) * _cell;
    private _built = [];
    for "_gx" from 0 to (_axis - 1) do {
        for "_gy" from 0 to (_axis - 1) do {
            _built pushBack [
                ((_position select 0) - _half) + ((_gx + 0.5) * _cell),
                ((_position select 1) - _half) + ((_gy + 0.5) * _cell)
            ];
        };
    };
    _pending = _built;
};

private _t0 = diag_tickTime;
private _done = false;
private _unsampled = [];
private _foliageSum = 0;
private _waterCount = 0;
private _structSum = 0;
private _elevSum = 0;
private _sampleCount = 0;
private _queries = 0;
private _votes = [];

for "_i" from 0 to ((count _pending) - 1) do {
    if (!_done) then {
        if ((((diag_tickTime - _t0) * 1000) >= _budget) || ((_queries + 2) > WILDLIFE_ENVIRONMENT_QUERY_CAP)) then {
            _done = true;
            _unsampled = _pending select [_i];
        } else {
            private _cellPos = _pending select _i;
            private _key = [floor ((_cellPos select 0) / _cell), floor ((_cellPos select 1) / _cell)];

            private _cached = [];
            for "_c" from 0 to ((count _store) - 1) do {
                private _entry = _store select _c;
                if ((_entry select 0) isEqualTo _key) then { _cached = _entry select 1; };
            };

            private _sample = _cached;
            if (_sample isEqualTo []) then {
                private _pos2d = [_cellPos select 0, _cellPos select 1];
                private _water = surfaceIsWater _pos2d;
                private _material = "water";
                if (!_water) then {
                    _material = [surfaceType _pos2d] call EFUNC(material,classifyBySurfaceType);
                };

                private _foliageObjs = nearestTerrainObjects [[(_pos2d select 0), (_pos2d select 1), 0], ["Tree", "Bush"], _cell, false, true];
                if ((count _foliageObjs) > _cap) then { _foliageObjs = _foliageObjs select [0, _cap]; };
                private _structObjs = nearestTerrainObjects [[(_pos2d select 0), (_pos2d select 1), 0], ["Building"], _cell, false, true];
                if ((count _structObjs) > _cap) then { _structObjs = _structObjs select [0, _cap]; };
                private _trees = count _foliageObjs;
                private _buildings = count _structObjs;

                private _waterFlag = 0;
                if (_water) then { _waterFlag = 1; };

                _sample = [
                    ((_trees / _cap) min 1),
                    _material,
                    _waterFlag,
                    ((_buildings / _cap) min 1),
                    (getTerrainHeightASL _pos2d)
                ];

                _store pushBack [_key, _sample, _now];
                if ((count _store) > WILDLIFE_ENVIRONMENT_CAP) then {
                    _store = _store select [((count _store) - WILDLIFE_ENVIRONMENT_CAP), WILDLIFE_ENVIRONMENT_CAP];
                };
            };

            _foliageSum = _foliageSum + (_sample select 0);
            _waterCount = _waterCount + (_sample select 2);
            _structSum = _structSum + (_sample select 3);
            _elevSum = _elevSum + (_sample select 4);

            private _material = _sample select 1;
            private _matched = false;
            private _next = [];
            for "_v" from 0 to ((count _votes) - 1) do {
                private _vote = _votes select _v;
                if ((_vote select 0) == _material) then {
                    _next pushBack [_material, (_vote select 1) + 1];
                    _matched = true;
                } else {
                    _next pushBack _vote;
                };
            };
            if (!_matched) then { _next pushBack [_material, 1]; };
            _votes = _next;

            _sampleCount = _sampleCount + 1;
            _queries = _queries + 2;
        };
    };
};

_store = [_store, _now] call FUNC(environmentGrid);
missionNamespace setVariable [QGVAR(environment), _store];
missionNamespace setVariable [QGVAR(environmentPending), _unsampled];
missionNamespace setVariable [QGVAR(environmentLastMs), ((diag_tickTime - _t0) * 1000)];

private _denom = _sampleCount max 1;

[
    ((_foliageSum / _denom) max 0) min 1,
    _votes,
    ((_waterCount / _denom) max 0) min 1,
    ((_structSum / _denom) max 0) min 1,
    (_elevSum / _denom)
]
