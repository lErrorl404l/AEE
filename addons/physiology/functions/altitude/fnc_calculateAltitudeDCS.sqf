#include "..\..\script_component.hpp"
/*
Altitude decompression sickness solver (issue #135).

Reuses the ZH-L16C 16-compartment tissue model from the diving system
(#118) by feeding it the ICAO barometric ambient pressure below 1 bar.
At altitude the tissues are supersaturated (P_tissue > P_amb).

DCS risk metric (Kumar/Waligora, Haske & Pilmanis 2002):
  R = P_tissue_N2 / P_ambient   (supersaturation ratio)
  DCS is rare below R ~ 1.5 and risk climbs steeply toward R ~ 2.0.
  The controlling compartment is the one with the HIGHEST R — at
  altitude that is the SLOWEST tissue, which holds its nitrogen longest
  while fast tissues off-gas.  (The diving a/b ceiling is a hyperbaric
  concept and its max-0 clamp zeroes at altitude anyway.)
  risk = clamp((R - 1.5) / 0.5, 0, 1)

DCS risk curve anchors (zero prebreathe, air, Haske & Pilmanis 2002):
  25,000 ft / 45 min  and  22,000 ft / 200 min  reach the 20% risk.
  Threshold: 21,000 ft (published curve limit; "no DCS below 18,000 ft"
  is the FAA rule of thumb).

Input:  [_altM, _tissues, _dtSec]
Output: [risk 0..1, R, newTissues]
*/
params [["_altM", 0, [0]], ["_tissues", [], [[]]], ["_dtSec", 1, [0]]];

private _pAmb = [_altM] call FUNC(calculateBarometricPressure);
private _step = [0, 0.79, 0, _tissues, 1.0, _pAmb] call FUNC(zh16cStep);
private _newTissues = _step select 0;

// ─── Supersaturation ratio: controlling compartment ──────────────────────
// Highest tissue N2 relative to ambient (the slowest tissue holds N2
// longest at altitude).
private _r = 0;
for "_i" from 0 to 15 do {
    private _pn2 = _newTissues select _i;
    private _ri = if (_pAmb > 0) then { _pn2 / _pAmb } else { 0 };
    _r = _r max _ri;
};

private _risk = (_r - 1.5) / 0.5;   // rare < 1.5, steep to 2.0
_risk = _risk max 0 min 1;

[_risk, _r, _newTissues]
