#include "..\..\script_component.hpp"

/*
Combat stress index (issue #110).

The stress is the engine suppression value, 0 to 1: the engine's own measure
of incoming fire near the unit.  No published study gives a weighting by which
physical fatigue or the group's casualties add to that arousal, so neither is
added; the inputs are kept for the call signature.  The degradation that
stress drives is sourced in fnc_getDecisionMultipliers (Rowland 1986).

Input:
  0: Number - suppression, 0 to 1 (engine getSuppression; the caller maps -1
              to 0)
  1: Number - fatigue, 0 to 1 (unused, see above)
  2: Number - casualty ratio, 0 to 1 (unused, see fnc_calculateMorale)

Returns:
  Number - stress index, 0 to 1
*/

params [
    ["_suppression", 0, [0]],
    ["_fatigue", 0, [0]],
    ["_casualtyRatio", 0, [0]]
];

(_suppression min 1) max 0
