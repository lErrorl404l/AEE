#include "..\..\script_component.hpp"

/*
Decision-quality multipliers from the stress index (issue #110).

Maps stress to four performance channels.  The channels are the physiological
degradation; they apply regardless of the unit's courage (Easterbrook 1959,
cue narrowing).  The band edges and the multiplier values are the issue's
modelling choice, UNSOURCED (grade U).  The shape, a monotone decline past an
optimum, is grounded in Yerkes & Dodson (1908) and Lupien et al. (2007).

Table (issue #110 spec):

    stress < 0.4   -> [1.0, 1.0, 1.0, 1.0]
    stress < 0.6   -> [0.9, 0.8, 0.7, 0.6]
    stress < 0.8   -> [0.7, 0.5, 0.4, 0.3]
    else           -> [0.5, 0.3, 0.2, 0.1]

Input:
  0: Number - stress index, 0 to 1

Returns:
  Array - [reaction, accuracy, spotting, firingRate], each 0 to 1
*/

params [["_stress", 0, [0]]];

private _table = [
    [1.0, 1.0, 1.0, 1.0],
    [0.9, 0.8, 0.7, 0.6],
    [0.7, 0.5, 0.4, 0.3],
    [0.5, 0.3, 0.2, 0.1]
];

private _band = 0;
if (_stress >= 0.4) then { _band = 1; };
if (_stress >= 0.6) then { _band = 2; };
if (_stress >= 0.8) then { _band = 3; };

_table select _band
