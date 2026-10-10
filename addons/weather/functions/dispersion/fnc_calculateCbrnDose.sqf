#include "..\..\script_component.hpp"

/*
CBRN inhalation dose accumulation and the exposure thresholds.

Source: FM 3-11, "Chemical Operations" (2003).  The inhaled dose is the
concentration-time product, Dose += C * dt with dt in minutes and C in
mg/m3, giving mg*min/m3.  An agent is lethal at 1.0 x LCt50 and
incapacitating at 0.1 x LCt50 (the FM 3-11 miosis/incapacitation tier).
The CBRN protection factor (fnc_getCbrnProtection) scales the inhaled
fraction, so a full kit blocks most of the agent.

Arguments:
  0: accumulated dose (NUMBER, mg*min/m3)
  1: concentration (NUMBER, mg/m3)
  2: time step (NUMBER, seconds)
  3: LCt50 (NUMBER, mg*min/m3)
  4: protection factor (NUMBER, 0..1 fraction blocked)

Returns [newDose, lethal, incapacitated].
*/

params [
    ["_dose", 0, [0]],
    ["_concentration", 0, [0]],
    ["_dtSeconds", 1, [0]],
    ["_lcT50", 1000, [0]],
    ["_protection", 0, [0]]
];

private _increment = _concentration * (_dtSeconds / 60) * (1 - _protection);
private _newDose = _dose + _increment;

private _lethal = _newDose >= _lcT50;
private _incapacitated = _newDose >= (0.1 * _lcT50);

[_newDose, _lethal, _incapacitated]
