#include "..\script_component.hpp"

/*
Ecology budget kernel (wildlife ecology).

Pure: no missionNamespace, no GVAR or EGVAR, no engine command, no random.
It answers one question for the budgeted ecology tick: may another animal be
processed this call?  The tick must always make progress, so the first animal
of a call is always allowed.  After that the count budget and the millisecond
budget both stop the sweep.  The tick keeps the unsolved remainder at the
front of the pending list, so no animal is dropped and none starves.

Arguments:
  0: Number - the animals already processed this call
  1: Number - the count budget
  2: Number - the elapsed milliseconds this call
  3: Number - the millisecond budget

Returns:
  Bool - true when another animal may be processed
*/

params [
    ["_processed", 0, [0]],
    ["_countBudget", 1, [0]],
    ["_elapsedMs", 0, [0]],
    ["_msBudget", 1, [0]]
];

if (_processed < 1) exitWith { true };
if (_processed >= ((round _countBudget) max 1)) exitWith { false };
if (_elapsedMs >= (_msBudget max 0)) exitWith { false };

true
