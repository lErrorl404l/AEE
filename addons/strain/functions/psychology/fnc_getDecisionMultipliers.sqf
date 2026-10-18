#include "..\..\script_component.hpp"

/*
Decision-quality multipliers from the stress index (issue #110).

Rowland (1986), "Assessments of combat degradation", RUSI Journal 131(2):
in historical combat, small arms achieved one-seventh to one-tenth of the
effectiveness the same weapons achieved in field trials without the enemy's
fire.  The mid value, 0.12, is the accuracy of a fully suppressed soldier;
accuracy falls linearly with stress from 1 to it.  No comparable published
figure exists for reaction time, spotting or rate of fire, so those channels
stay at 1.

Input:
  0: Number - stress index, 0 to 1

Returns:
  Array - [reaction, accuracy, spotting, firingRate], each 0 to 1
*/

params [["_stress", 0, [0]]];

private _COMBAT_EFFECTIVENESS = 0.12;  // Rowland 1986: 1/7 to 1/10

[1, 1 - ((_stress min 1) max 0) * (1 - _COMBAT_EFFECTIVENESS), 1, 1]
