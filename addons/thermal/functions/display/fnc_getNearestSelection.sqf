#include "..\..\script_component.hpp"
/*
 * Nearest thermal selection (issue #204).
 *
 * Selects the one selection whose model-space point is closest to a given
 * point in the same frame.  The four local heat sources use it to warm the
 * part they physically touch: the impact face, the contact face, the part
 * an exhaust plume washes over.  No selection name is matched and no list
 * order is read, so a vehicle's part order never decides which part heats.
 *
 * Pure array arithmetic: the distance is compared as a squared distance, so
 * the function makes no engine call and stays cheap inside the throttled
 * pair loops.  Points come from the per-class cache
 * fnc_getThermalSelectionPoints, so the model is walked once per class.
 *
 * Params:
 *   0: _names (ARRAY of STRING) - selection names
 *   1: _points (ARRAY of ARRAY) - model-space points, same order as _names
 *   2: _refPos (ARRAY) - the query point in the same model space
 *
 * Returns: STRING - the nearest selection name, or "" when no point is
 *   available.  A point at the model origin is a real point and is eligible.
 */
params [
    ["_names", [], [[]]],
    ["_points", [], [[]]],
    ["_refPos", [0, 0, 0], [[]]]
];

if ((_names isEqualTo []) || (_points isEqualTo [])) exitWith { "" };

// A finite ceiling above any model-space distance squared, so the first
// point always wins the first comparison.  Model space reaches a few tens
// of metres; 1e9 m^2 is far above that and needs no lookup.
private _bestD2 = 1000000000;
private _best = "";
private _n = (count _names) min (count _points);
for "_i" from 0 to (_n - 1) do {
    private _p = _points select _i;
    private _dx = (_p select 0) - (_refPos select 0);
    private _dy = (_p select 1) - (_refPos select 1);
    private _dz = (_p select 2) - (_refPos select 2);
    private _d2 = (_dx * _dx) + (_dy * _dy) + (_dz * _dz);
    if (_d2 < _bestD2) then {
        _bestD2 = _d2;
        _best = _names select _i;
    };
};

_best
