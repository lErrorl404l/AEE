#include "..\..\script_component.hpp"

/*
Effective spotting after the stress decision multiplier (issue #110).

The unit's engine spotDistance skill scaled by the spotting multiplier from
fnc_getDecisionMultipliers.  The degradation applies regardless of courage:
"A suppressed soldier with high Courage still spots less" (issue #110).  The
driver publishes this value.  It never writes the engine skill: setSkill is
global and would double-count the engine's own suppression response.

Input:
  0: Number - the engine spotDistance skill, 0 to 1
  1: Number - the spotting multiplier, 0 to 1

Returns:
  Number - effective spotting, 0 to 1
*/

params [
    ["_spotDistanceSkill", 0, [0]],
    ["_spottingMultiplier", 1, [0]]
];

(_spotDistanceSkill * _spottingMultiplier) min 1 max 0
