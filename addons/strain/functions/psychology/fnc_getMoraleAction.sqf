#include "..\..\script_component.hpp"

/*
Morale action gate (issue #110).

Maps morale to a behavioural response.  Courage shifts the effective morale: a
high-courage soldier holds the line at lower morale, so courage gates the
behavioural response, not the physiological one (issue #110).  The thresholds
and the courage weight are the issue's modelling choice, UNSOURCED (grade U).

Gate (issue #110 spec):

    effective morale < 0.15 -> 2 break (retreat / surrender)
    effective morale < 0.30 -> 1 seek cover
    else                    -> 0 hold

Input:
  0: Number - morale index, 0 to 1
  1: Number - the engine courage skill, 0 to 1 (the engine mid default is 0.5)

Returns:
  Number - action id: 0 hold, 1 seek cover, 2 break
*/

params [
    ["_morale", 0, [0]],
    ["_courage", 0.5, [0]]
];

private _COURAGE_WEIGHT = 0.2;  // UNSOURCED (issue #110)
private _COVER_MORALE = 0.30;   // UNSOURCED (issue #110)
private _BREAK_MORALE = 0.15;   // UNSOURCED (issue #110)

// The courage skill is centred at 0.5, so a high-courage soldier resists the
// gate and a low-courage soldier yields.
private _effective = _morale + (_courage - 0.5) * _COURAGE_WEIGHT;
_effective = _effective min 1 max 0;

private _action = 0;
if (_effective < _COVER_MORALE) then { _action = 1; };
if (_effective < _BREAK_MORALE) then { _action = 2; };

_action
