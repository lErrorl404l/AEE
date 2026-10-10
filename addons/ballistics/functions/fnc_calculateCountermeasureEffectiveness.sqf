#include "..\script_component.hpp"

/*
Countermeasure seduction probability (pure).

A decoy (flare or chaff) can only seduce the seeker when its signature
exceeds the target's.  Given that gate passes, the switch probability is the
base effectiveness for the seeker generation:

    seduced when  decoySignal > targetSignal
    P_switch      = baseEffectiveness   (else 0)

The decoySignal is the flare radiant intensity (fnc_calculateFlareIntensity)
for an IR seeker, or the chaff cloud RCS (fnc_calculateChaffCrossSection)
for a radar seeker; targetSignal is the same quantity for the target.  The
comparison is like-for-like, so a caller passes one unit on both sides.

BASE EFFECTIVENESS IS UNSOURCED.  The issue #131 gives these bands as "tuning
values", and no named source supports them:
    flare vs first-generation IR  0.6 to 0.9
    flare vs imaging IR           0.1 to 0.3
    chaff vs first-generation radar 0.5 to 0.8
    chaff vs modern radar         0.1 to 0.4
    DRFM vs radar                 0.4 to 0.7
The caller supplies the base for its seeker generation; this kernel only
applies the seduction gate and clamps the probability to 0..1.

Arguments:
  0: _decoySignal       (NUMBER) decoy signature (W/sr for a flare, m2 for
                        chaff)
  1: _targetSignal      (NUMBER) target signature, same unit as the decoy
  2: _baseEffectiveness (NUMBER) generation base switch probability, 0..1

Return Value: NUMBER - seduction probability in 0..1.  Returns 0 when the
decoy does not exceed the target.
Public: No
*/

params [
    ["_decoySignal", 0, [0]],
    ["_targetSignal", 0, [0]],
    ["_baseEffectiveness", 0, [0]]
];

if (_decoySignal <= _targetSignal) exitWith { 0 };

(_baseEffectiveness max 0) min 1
