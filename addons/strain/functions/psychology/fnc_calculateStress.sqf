#include "..\..\script_component.hpp"

/*
Combat stress index (issue #110).

The physiological arousal that degrades a soldier's decision quality.  The
engine supplies the suppression value; the model adds the fatigue and the
casualty pressure of the unit's group.  The model is memoryless: stress is an
instantaneous function of the three inputs, so no time step is needed.

Formula (issue #110 spec):

    stress = clamp(suppression + 0.3*fatigue + 0.3*casualtyRatio, 0, 1)

The additive form and the 0.3 weights are the issue's modelling choice.  No
published source states an additive stress index, so both are UNSOURCED
(grade U).  The curve SHAPE they feed is grounded in Yerkes & Dodson (1908)
and Lupien et al. (2007); see the dossier.

Input:
  0: Number - suppression, 0 to 1 (engine getSuppression; the caller maps -1
              to 0)
  1: Number - fatigue, 0 to 1 (engine getFatigue)
  2: Number - casualty ratio, 0 to 1 (group casualties / initial strength)

Returns:
  Number - stress index, 0 to 1
*/

params [
    ["_suppression", 0, [0]],
    ["_fatigue", 0, [0]],
    ["_casualtyRatio", 0, [0]]
];

private _W_FATIGUE = 0.3;   // UNSOURCED (issue #110)
private _W_CASUALTY = 0.3;  // UNSOURCED (issue #110)

private _stress = _suppression + _W_FATIGUE * _fatigue + _W_CASUALTY * _casualtyRatio;

_stress min 1 max 0
