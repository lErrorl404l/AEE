#include "..\..\script_component.hpp"
/*
 * Sensor-resolution level of detail (issue #204, fusion outline).
 *
 * Ported from the _lvS block in workshop 3811605241 whale_ecoti_llll
 * functions/fn_drawOutlines.sqf.  A thermal sensor resolves a target only
 * while it covers enough pixels on the detector: 60 px and up is the full
 * skeleton, 25 to 60 is medium, 10 to 25 is simplified, and below 10 the
 * target is a blob.  The caller computes the target height in sensor pixels
 * as 1.8 / _mpp, where _mpp is the metres one detector pixel covers at range.
 * Pure: no engine state, so the harness can execute it.
 *
 * Params:
 *   0: _hSens (SCALAR) - target height in sensor pixels.
 *
 * Returns: SCALAR 0..3 (0 = full detail, 3 = blob).
 */
params [["_hSens", 0, [0]]];

if (_hSens >= 60) exitWith { 0 };
if (_hSens >= 25) exitWith { 1 };
if (_hSens >= 10) exitWith { 2 };
3
