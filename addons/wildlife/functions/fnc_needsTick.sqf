#include "..\script_component.hpp"

/*
Animal needs kernel (wildlife ecology).

Pure: no missionNamespace, no GVAR or EGVAR, no engine command.  Hunger and
thirst rise with the elapsed time and the rates, clamped to 0 to 1.  The goal
is the resource the animal wants: water (2) wins above the thirst threshold,
food (1) above the hunger threshold, else none (0).

The thresholds are modelling choices, UNSOURCED, held here so the driver
owns no policy.  See the per-constant register in the dossier.

Arguments:
  0: Number - hunger, 0 to 1
  1: Number - thirst, 0 to 1
  2: Number - the elapsed time, seconds
  3: Number - the hunger rate, per second
  4: Number - the thirst rate, per second

Returns:
  Array - [hunger, thirst, goal] with goal 0 none, 1 food, 2 water
*/

params [
    ["_hunger", 0, [0]],
    ["_thirst", 0, [0]],
    ["_dt", 0, [0]],
    ["_hungerRate", 0.02, [0]],
    ["_thirstRate", 0.03, [0]]
];

private _hungerNext = ((_hunger + (_hungerRate * _dt)) max 0) min 1;
private _thirstNext = ((_thirst + (_thirstRate * _dt)) max 0) min 1;

private _goal = 0;
if (_thirstNext > 0.6) then {
    _goal = 2;
} else {
    if (_hungerNext > 0.4) then {
        _goal = 1;
    };
};

[_hungerNext, _thirstNext, _goal]
