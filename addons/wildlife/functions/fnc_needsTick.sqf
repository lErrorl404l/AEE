#include "..\script_component.hpp"

/*
Animal needs kernel (wildlife ecology).

Pure: no missionNamespace, no GVAR or EGVAR, no engine command.  Hunger and
thirst rise with the elapsed time and the rates, clamped to 0 to 1.  The goal
is the resource the animal wants: water (2) wins above the thirst threshold,
food (1) above the hunger threshold, else none (0).

Each need is the fraction of its own interval between bouts that has elapsed,
so the animal seeks the resource when its need reaches 1 and no threshold is
invented.  Water wins when both are due, because an animal dies of thirst
long before it starves.

The two intervals are measured: a deer feeds about five times in 24 h, its
low-fibre browse passing the rumen quickly, and drinks about once a day in
summer heat (Hervert and Krausman 1986 for the desert mule deer water visits;
the five feeding bouts are the standard whitetail figure).  The ratio of the
two, 5 to 1, is what the caller's two rates carry: the default thirst rate is
the default hunger rate divided by five.  The absolute pace is a gameplay
setting, not a measured quantity.

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
if (_thirstNext >= 1) then {
    _goal = 2;
} else {
    if (_hungerNext >= 1) then {
        _goal = 1;
    };
};

[_hungerNext, _thirstNext, _goal]
