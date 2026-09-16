#include "..\script_component.hpp"

/*
Shooter stability index from environmental and physiological stressors.

Combines three literature-anchored factors into a 0..1 stability index
via geometric mean (the human-reliability standard combination, SPAR-H
sub-additivity; NUREG/CR-6883).

Factors and their published anchors:

  COLD (skin temperature proxy — ambient temperature is used because no
  skin-temperature model exists yet; this understates hand cooling in
  wind, so the curve is deliberately conservative):
    T >= 15 degC            -> 1.0     (manual dexterity onset threshold,
                                        Heus, Daanen & Havenith 1995,
                                        Appl Ergon 26(1):5-13, PMID 15676995)
    8..15 degC              -> 1.0 -> 0.6 linear
    < 8 degC                -> 0.6 -> 0.3 floor (severe impairment below
                                        8 degC, Fox 1967; marksmanship
                                        intact at finger 10.8 degC,
                                        Tikuisis & Keefe 2007,
                                        PMID 17484343)

  HEAT (WBGT — a VIGILANCE factor, not a precision factor; direct
  marksmanship trials show no precision loss at core 39 degC, so the
  curve only bites at ACGIH-TLV levels):
    WBGT <= 29 degC         -> 1.0     (ACGIH 2022 TLV, moderate work)
    29..42 degC             -> 1.0 -> 0.6 linear (perceptual-motor onset
                                        ~30-33 degC, vigilance limit
                                        42.8 degC, Hancock & Vasmatzidis
                                        2003, Int J Hyperthermia 19(3))
    > 42 degC               -> 0.6 floor

  FATIGUE (hours awake — anchored to marksmanship trials):
    0..16 h                 -> 1.0     (no measurable precision loss)
    16..24 h                -> 1.0 -> 0.85  (22 h -> precision loss onset,
                                             Tikuisis 2004)
    24..48 h                -> 0.85 -> 0.6
    48..72 h                -> 0.6 -> 0.35 (shot group x3.35 at 73 h,
                                             Tharion, Shukitt-Hale &
                                             Lieberman 2003, PMID 12688447;
                                             ineffective 48-72 h,
                                             Haslam 1984, PMID 6721809)
    > 72 h                  -> 0.3 floor

  WIND is NOT a stability factor.  Crosswind deflects the ROUND, not the
  shooter: at 300 m a 25 kt wind drifts a 5.56 round ~86 cm (FM 3-22.9).
  That is a ballistics miss-probability effect, already modelled by
  aee_ballistics_fnc_calculateCrosswindBallistics.  Including it here
  would double-count and model the wrong quantity.

Combination: geometric mean of the three factors.  This preserves the
"all factors matter" property, stays in [0,1], and is less punishing
than a straight product — matching the sub-additivity the SPAR-H
correction provides.

Input:  []
Output: stability index 0..1
Sets:   QEGVAR(core,shooterStability)
*/

// ─── Read state ───────────────────────────────────────────────────────────
private _ambientC  = missionNamespace getVariable [QEGVAR(core,currentTemperature), 15];
if !(_ambientC isEqualType 0) then { _ambientC = 15; };
private _wbgt      = missionNamespace getVariable [QEGVAR(core,currentWBGT), 15];
if !(_wbgt isEqualType 0) then { _wbgt = 15; };
private _wakeHours = missionNamespace getVariable [QGVAR(wakefulnessHours), 0];
if !(_wakeHours isEqualType 0) then { _wakeHours = 0; };

// ─── Cold factor ──────────────────────────────────────────────────────────
private _cold = 1.0;
if (_ambientC < 15) then {
    if (_ambientC >= 8) then {
        _cold = linearConversion [15, 8, _ambientC, 1.0, 0.6, true];
    } else {
        _cold = linearConversion [8, -10, _ambientC, 0.6, 0.3, true];
    };
};
_cold = _cold max 0.3 min 1.0;

// ─── Heat (vigilance) factor ──────────────────────────────────────────────
private _heat = 1.0;
if (_wbgt > 29) then {
    if (_wbgt <= 42) then {
        _heat = linearConversion [29, 42, _wbgt, 1.0, 0.6, true];
    } else {
        _heat = 0.6;
    };
};
_heat = _heat max 0.6 min 1.0;

// ─── Fatigue factor (hours awake) ─────────────────────────────────────────
private _fatigue = 1.0;
if (_wakeHours > 16) then {
    switch (true) do {
        case (_wakeHours <= 24): { _fatigue = linearConversion [16, 24, _wakeHours, 1.0, 0.85, true]; };
        case (_wakeHours <= 48): { _fatigue = linearConversion [24, 48, _wakeHours, 0.85, 0.6, true]; };
        case (_wakeHours <= 72): { _fatigue = linearConversion [48, 72, _wakeHours, 0.6, 0.35, true]; };
        default                 { _fatigue = 0.3; };
    };
};
_fatigue = _fatigue max 0.3 min 1.0;

// ─── Geometric mean ───────────────────────────────────────────────────────
private _stability = (_cold * _heat * _fatigue) ^ (1 / 3);
_stability = _stability max 0.2 min 1.0;

missionNamespace setVariable [QEGVAR(core,shooterStability), _stability];

_stability
