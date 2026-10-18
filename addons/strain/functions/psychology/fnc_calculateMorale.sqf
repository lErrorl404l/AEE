#include "..\..\script_component.hpp"

/*
Combat morale index (issue #110).

The unit's remaining will to fight, from the group's casualties against the
US Army breakpoint table of FM 105-5, Maneuver Control (December 1967, as
reproduced by the Dupuy Institute, "C-WAM 4 (Breakpoints)", 2018): once a
unit reaches about 40 percent casualties its chance of breaking approaches
100 percent.  Morale falls linearly to 0 at that breakpoint:

    morale = clamp(1 - casualtyRatio / 0.40 + missionBonus, 0, 1)

The mission bonus is a scenario designer's offset (a mission input, not a
physical constant).  Fatigue is not applied: no published source links the
engine's short-term stamina fatigue to morale (Dupuy's QJM exhaustion factor
counts days in combat, a different quantity).

Input:
  0: Number - casualty ratio, 0 to 1
  1: Number - fatigue, 0 to 1 (unused, see above)
  2: Number - mission bonus, a signed morale offset (default 0)

Returns:
  Number - morale index, 0 to 1
*/

params [
    ["_casualtyRatio", 0, [0]],
    ["_fatigue", 0, [0]],
    ["_missionBonus", 0, [0]]
];

private _BREAK_CASUALTIES = 0.40;  // FM 105-5 (1967): breaking approaches certainty

private _morale = 1 - _casualtyRatio / _BREAK_CASUALTIES + _missionBonus;

(_morale min 1) max 0
