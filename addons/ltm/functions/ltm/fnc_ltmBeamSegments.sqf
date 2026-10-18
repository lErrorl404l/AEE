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
 * returns the same chain as drawable dashes, clipped to the real
 * designator-to-target range so it never overruns the target (issue #309).
 * It replaces the source p3d beam model, which cannot be shipped, so no
 * object is created.
 *
 * Params:
 *   0: _originASL (ARRAY) - designator position in ASL.
 *   1: _targetASL (ARRAY) - laser target position in ASL.
 *   2: _count (SCALAR)    - maximum number of dashes (source: 21).
 *   3: _step (SCALAR)     - dash length and spacing in metres (source: 500).
 *
 * Returns: ARRAY of [startASL, endASL] pairs, or [] for degenerate input.
 *          The chain is at most _count dashes and at most (_count * _step)
 *          metres long; only the final dash may be shorter than _step.
 */
params [
    ["_originASL", [], [[]]],
    ["_targetASL", [], [[]]],
    ["_count", 21, [0]],
    ["_step", 500, [0]]
];

if ((_originASL isEqualTo []) || (_targetASL isEqualTo [])) exitWith { [] };
if (_count <= 0) exitWith { [] };
if (_step <= 0) exitWith { [] };

private _delta = _targetASL vectorDiff _originASL;
private _distance = vectorMagnitude _delta;
if (_distance < 0.001) exitWith { [] };

private _dir = vectorNormalized _delta;

// Clip the chain to the designator-to-target distance.  The source model
// placed a fixed 21 * 500 m = 10.5 km row of beam objects whatever the real
// range, so the dashes always ran far past the target.  The beam now stops
// at the target: full dashes stay _step long and a short final dash is
// truncated at the target (issue #309).
private _reach = _distance min (_count * _step);
private _segments = [];
private _offset = 0;
while { _offset < _reach } do {
    private _end = (_offset + _step) min _reach;
    _segments pushBack [
        _originASL vectorAdd (_dir vectorMultiply _offset),
        _originASL vectorAdd (_dir vectorMultiply _end)
    ];
    _offset = _end;
};

_segments
