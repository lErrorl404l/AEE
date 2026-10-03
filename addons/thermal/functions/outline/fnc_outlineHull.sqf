#include "..\..\script_component.hpp"
/*
 * Convex hull of projected screen points (issue #204, fusion outline).
 *
 * Ported from workshop 3811605241 whale_ecoti_llll functions/fn_convexHull.sqf:
 * the Andrew monotone chain, O(n log n), returns the INDICES of the hull
 * points in the input array.  The fusion outline uses it to tie the sampled
 * skeleton points of one hot target into the outline that hugs it, instead of
 * drawing a box.  aee feeds it its own projected selection skeleton.
 *
 * The source's `#` index form is written here as `select`, and the source's
 * reverse pass is an index walk, so the harness in tools/tests/sqf_lite.py can
 * execute the real kernel.  The chain itself is unchanged.
 *
 * Params:
 *   0: _pts (ARRAY of [x, y]) - projected screen points.
 *
 * Returns: ARRAY of indices into _pts, counter-clockwise.
 */
params [["_pts", [], [[]]]];

private _n = count _pts;

// Fewer than three points: degenerate to a line or a point, return all.
if (_n < 3) exitWith {
    private _all = [];
    { _all pushBack _forEachIndex; } forEach _pts;
    _all
};

// Pack to [x, y, original index], then sort by x and then y.
private _keyed = [];
{ _keyed pushBack [_x select 0, _x select 1, _forEachIndex]; } forEach _pts;
_keyed sort true;

// Lower hull: pop the middle point whenever the chain turns right or flat.
private _lower = [];
{
    private _b = _x;
    private _keep = true;
    while { _keep } do {
        if ((count _lower) >= 2) then {
            private _o = _lower select -2;
            private _a = _lower select -1;
            private _cross = (((_a select 0) - (_o select 0)) * ((_b select 1) - (_o select 1))) - (((_a select 1) - (_o select 1)) * ((_b select 0) - (_o select 0)));
            if (_cross <= 0) then {
                _lower deleteAt ((count _lower) - 1);
            } else {
                _keep = false;
            };
        } else {
            _keep = false;
        };
    };
    _lower pushBack _b;
} forEach _keyed;

// Upper hull: walk the sorted points in reverse order.
private _upper = [];
{
    private _b = _keyed select ((count _keyed) - 1 - _forEachIndex);
    private _keep = true;
    while { _keep } do {
        if ((count _upper) >= 2) then {
            private _o = _upper select -2;
            private _a = _upper select -1;
            private _cross = (((_a select 0) - (_o select 0)) * ((_b select 1) - (_o select 1))) - (((_a select 1) - (_o select 1)) * ((_b select 0) - (_o select 0)));
            if (_cross <= 0) then {
                _upper deleteAt ((count _upper) - 1);
            } else {
                _keep = false;
            };
        } else {
            _keep = false;
        };
    };
    _upper pushBack _b;
} forEach _keyed;

// Join, dropping the duplicated end point of each chain.
if (_lower isNotEqualTo []) then { _lower deleteAt ((count _lower) - 1); };
if (_upper isNotEqualTo []) then { _upper deleteAt ((count _upper) - 1); };

private _hull = _lower + _upper;

private _out = [];
{ _out pushBack (_x select 2); } forEach _hull;
_out
