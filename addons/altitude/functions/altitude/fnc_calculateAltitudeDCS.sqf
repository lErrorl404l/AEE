#include "..\..\script_component.hpp"
/*
Altitude decompression sickness solver (issue #135, #280).

Reuses the ZH-L16C 16-compartment tissue model from the diving system
(#118) by feeding it the ICAO barometric ambient pressure below 1 bar.
At altitude the tissues are supersaturated (P_tissue > P_amb).

DCS risk metric (Kumar/Waligora, Haske & Pilmanis 2002):
  The instantaneous supersaturation ratio is not a risk. DCS is a dose:
  the supersaturation must be HELD for a time, so the hazard is the
  severity of the ratio integrated over the exposure, and the risk is the
  survival form of that hazard.
    R        = P_tissue_N2 / P_ambient   (supersaturation ratio)
    severity = max(0, (R - 1.5) / 0.5)   rare below R ~ 1.5, 1.0 at R ~ 2.0
    hazard   = severity ^ 1.2 / 10352    per second
    risk     = 1 - exp(-integral hazard dt)
  The exponential form is additive: many short steps accumulate the same
  exposure as one long step, so a caller that integrates at 1 Hz publishes
  the same episode risk either way.
  The controlling compartment is the one with the HIGHEST R. At
  altitude that is the SLOWEST tissue, which holds its nitrogen longest
  while fast tissues off-gas.  (The diving a/b ceiling is a hyperbaric
  concept and its max-0 clamp zeroes at altitude anyway.)

DCS risk curve anchors (zero prebreathe, air, Haske & Pilmanis 2002):
  25,000 ft / 45 min  and  22,000 ft / 200 min  each reach the 20% risk.
  The hazard exponent (1.2) and the full-severity time constant
  (10,352 s) are fitted to those two anchors: the curve returns 20.0% and
  20.1%.  A single 1 s step at 25,000 ft is 0.009%, so the risk rises with
  the exposure instead of jumping to the ratio.
  Threshold: 21,000 ft (published curve limit; "no DCS below 18,000 ft"
  is the FAA rule of thumb).

Input:  [_altM, _tissues, _dtSec]
Output: [risk 0..1, R, newTissues]
  risk       - the DCS risk the _dtSec exposure added
  R          - the end-of-step controlling supersaturation ratio
  newTissues - the tissue state at the end of the step
*/
params [["_altM", 0, [0]], ["_tissues", [], [[]]], ["_dtSec", 1, [0]]];

private _pAmb = [_altM] call FUNC(calculateBarometricPressure);

// The two constants fitted to the Haske & Pilmanis anchors (header).
private _hazardExp = 1.2;
private _calibSec = 10352;

// ─── Exposure-integrated hazard ──────────────────────────────────────────
// The interval is walked in sub-steps of at most 30 s, bounded at 120
// sub-steps so a long single call stays cheap. A tissue step composes
// exactly, so the sub-step count changes only the quadrature of the
// hazard integral, never the tissue end state.
private _stepSec = _dtSec max 0;
private _nSub = (ceil (_stepSec / 30)) min 120;
private _subSec = if (_nSub > 0) then { _stepSec / _nSub } else { 0 };
private _dose = 0;
// A zero-length step normalises the state only: the solver builds the
// surface baseline for an empty _tissues and leaves a held state unchanged.
private _newTissues = ([0, 0.79, 0, _tissues, 1.0, _pAmb, 0] call EFUNC(physiology,zh16cStep)) select 0;
for "_s" from 1 to _nSub do {
    private _rSub = 0;
    for "_i" from 0 to 15 do {
        private _ri = if (_pAmb > 0) then { (_newTissues select _i) / _pAmb } else { 0 };
        _rSub = _rSub max _ri;
    };
    private _severity = (_rSub - 1.5) / 0.5;   // rare below 1.5, 1.0 at 2.0
    if (_severity > 0) then {
        _dose = _dose + ((_severity ^ _hazardExp) * _subSec);
    };
    _newTissues = ([0, 0.79, 0, _newTissues, 1.0, _pAmb, _subSec] call EFUNC(physiology,zh16cStep)) select 0;
};

// ─── End-of-step ratio: controlling compartment ──────────────────────────
// Highest tissue N2 relative to ambient (the slowest tissue holds N2
// longest at altitude).
private _r = 0;
for "_i" from 0 to 15 do {
    private _riEnd = if (_pAmb > 0) then { (_newTissues select _i) / _pAmb } else { 0 };
    _r = _r max _riEnd;
};

private _risk = 1 - exp (-_dose / _calibSec);
_risk = _risk max 0 min 1;

[_risk, _r, _newTissues]
