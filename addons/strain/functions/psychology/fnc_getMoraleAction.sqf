#include "..\..\script_component.hpp"

/*
Morale action gate (issue #110).

FM 105-5, Maneuver Control (December 1967; Dupuy Institute 2018): an attacking
unit at about 20 percent casualties is almost certain to halt, and a unit at
about 40 percent is almost certain to break.  On the morale scale of
fnc_calculateMorale (0 at 40 percent casualties) those are morale 0.5 and 0:

    morale <= 0    -> 2 break (retreat / surrender)
    morale <  0.5  -> 1 seek cover (halt)
    else           -> 0 hold

The engine courage skill already drives the engine's own fleeing, so it is not
applied again here; it is kept for the call signature.

Input:
  0: Number - morale index, 0 to 1
  1: Number - the engine courage skill, 0 to 1 (unused, see above)

Returns:
  Number - action id: 0 hold, 1 seek cover, 2 break
*/

params [
    ["_morale", 0, [0]],
    ["_courage", 0.5, [0]]
];

private _HALT_MORALE = 1 - 0.20 / 0.40;  // FM 105-5: halt at 20 % casualties

private _action = 0;
if (_morale < _HALT_MORALE) then { _action = 1; };
if (_morale <= 0) then { _action = 2; };

_action
