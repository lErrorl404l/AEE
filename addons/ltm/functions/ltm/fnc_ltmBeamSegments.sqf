#include "..\..\script_component.hpp"
/*
 * Laser target marker beam geometry.
 *
 * Builds the dashes of a laser target marker as [startASL, endASL] pairs
 * along the line from the designator to the laser target.  This is the pure
 * geometry kernel.  The engine callers pass real positions.
 *
 * Ported from workshop 2041057379 A3TI/LTM/fn_createLTM.sqf.  The source
 * places 21 beam objects 500 m apart along the laser line.  This kernel
 * returns the same 21 nodes as drawable dashes.  It replaces the source p3d
 * beam model, which cannot be shipped, so no object is created.
 *
 * Params:
 *   0: _originASL (ARRAY) - designator position in ASL.
 *   1: _targetASL (ARRAY) - laser target position in ASL.
 *   2: _count (SCALAR)    - number of dashes (source: 21).
 *   3: _step (SCALAR)     - dash length and spacing in metres (source: 500).
 *
 * Returns: ARRAY of [startASL, endASL] pairs, or [] for degenerate input.
 */
params [
    ["_originASL", [], [[]]],
    ["_targetASL", [], [[]]],
    ["_count", 21, [0]],
    ["_step", 500, [0]]
];

if ((_originASL isEqualTo []) || (_targetASL isEqualTo [])) exitWith { [] };
if (_count <= 0) exitWith { [] };

private _delta = _targetASL vectorDiff _originASL;
if ((vectorMagnitude _delta) < 0.001) exitWith { [] };

private _dir = vectorNormalized _delta;
private _segments = [];
for "_i" from 0 to (_count - 1) do {
    private _start = _originASL vectorAdd (_dir vectorMultiply (_i * _step));
    private _end = _start vectorAdd (_dir vectorMultiply _step);
    _segments pushBack [_start, _end];
};

_segments
