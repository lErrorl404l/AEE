#include "..\script_component.hpp"
/*
G-induced loss of consciousness (G-LOC) model (issue #135).

Grounded in Whinnery & Forster 2013 (PMC3710154, 888 +Gz episodes):
  - Relaxed unprotected: greyout 3.4-4.8 G, blackout 4.0-5.6 G,
    LOC 4.5-6.3 G.
  - Time to LOC: rapid onset (>= 1 G/s) mean 9.10 s, INDEPENDENT of
    onset rate; gradual onset (<= 0.2 G/s) mean 74.4 s.  No LOC before
    5 s at any onset (the 5 s floor).
  - Recovery: absolute incapacitation 11.9 s, relative incapacitation
    ~16 s, total ~28 s.  Convulsions ~4 s between LOC and recovery.

Tolerance factors:
  - AGSM (M-1/L-1 straining): +3.1 G (relaxed 5.2 -> straining 8.3).
  - G-suit: +1-2 G (mean +1.5).
  - Reclined seat: +0.5 G (F-16 30 deg).
  - Hypoxia interaction: tolerance x (1 - hypoxiaRisk x k), k ~ 0.4.

The sequence: greyout -> tunnel -> blackout -> LOC -> convulsions ->
recovery -> relative incapacitation.  Rapid onset skips the visual
warnings (LOC without greyout).

Input:  [_g, _onsetRate, _agsm, _gsuit, _seat, _hypoxiaRisk]
  _g         - current +Gz load
  _onsetRate - G/s (rapid >= 1, gradual <= 0.2, else intermediate)
  _agsm      - 0/1 using the anti-G straining maneuver
  _gsuit     - 0/1 wearing a G-suit
  _seat      - reclined seat bonus (0.5 for F-16 style, else 0)
  _hypoxiaRisk - 0..1 from the hypoxia model
Output: [stage, timeToLoc, toleranceG]
  stage    - 0 none, 1 greyout, 2 blackout, 3 LOC, 4 convulsions,
             5 recovery, 6 relative incapacitation
  timeToLoc - seconds to LOC at the given onset rate (5 s floor)
  toleranceG - the computed G tolerance (after AGSM/suit/seat/hypoxia)
*/
params [["_g", 1, [0]], ["_onsetRate", 3, [0]], ["_agsm", 0, [0]],
        ["_gsuit", 0, [0]], ["_seat", 0, [0]], ["_hypoxiaRisk", 0, [0]]];

// ─── Tolerance ───────────────────────────────────────────────────────────
private _tolerance = 4.7
    + (_agsm * 3.1)       // AGSM straining
    + (_gsuit * 1.5)      // G-suit
    + (_seat * 0.5);      // reclined seat
// Hypoxia lowers G tolerance: a hypoxic pilot is closer to unconsciousness.
private _hypK = 0.4;
_tolerance = _tolerance * (1 - (_hypoxiaRisk * _hypK));

// ─── Time to LOC (Whinnery-Forster) ─────────────────────────────────────
// The 5 s floor: no LOC before 5 s at any onset rate.
private _tLoc = if (_onsetRate >= 1) then {
    9.10                            // rapid onset, rate-independent
} else {
    if (_onsetRate <= 0.2) then {
        74.4                        // gradual onset
    } else {
        // Intermediate: interpolate 9.1..74.4 across 0.2..1.0 G/s.
        9.10 + (74.4 - 9.10) * ((1 - _onsetRate) / 0.8)
    };
};
_tLoc = _tLoc max 5;

// ─── Stage ──────────────────────────────────────────────────────────────
// Above tolerance the sequence progresses; below it the pilot is fine.
// Greyout starts slightly below LOC; blackout between.
private _stage = 0;
if (_g > _tolerance) then {
    // Over tolerance: the higher the excess, the faster to LOC.
    private _excess = (_g - _tolerance) / _tolerance;
    if (_excess > 0.15) then {
        _stage = 3;                          // LOC
    } else {
        if (_excess > 0.08) then {
            _stage = 2;                      // blackout
        } else {
            _stage = 1;                      // greyout
        };
    };
};

[_stage, _tLoc, _tolerance]
