#include "..\..\script_component.hpp"

/*
Combat morale index (issue #110).

The unit's willingness to keep fighting.  Casualties and fatigue reduce it; a
mission bonus raises it.  The model is memoryless.

Formula (issue #110 spec):

    morale = clamp(1 - 0.5*casualtyRatio - 0.3*fatigue + missionBonus, 0, 1)

The form and the 0.5 and 0.3 weights are the issue's modelling choice,
UNSOURCED (grade U).  The qualitative basis is Wainstein (1986), IDA P-1903:
casualties are one of five factors that put a unit out of action, and morale
is the most important of them.  See the dossier.

Input:
  0: Number - casualty ratio, 0 to 1
  1: Number - fatigue, 0 to 1
  2: Number - mission bonus, a signed morale offset (default 0)

Returns:
  Number - morale index, 0 to 1
*/

params [
    ["_casualtyRatio", 0, [0]],
    ["_fatigue", 0, [0]],
    ["_missionBonus", 0, [0]]
];

private _W_CASUALTY = 0.5;  // UNSOURCED (issue #110)
private _W_FATIGUE = 0.3;   // UNSOURCED (issue #110)

private _morale = 1 - _W_CASUALTY * _casualtyRatio - _W_FATIGUE * _fatigue + _missionBonus;

_morale min 1 max 0
