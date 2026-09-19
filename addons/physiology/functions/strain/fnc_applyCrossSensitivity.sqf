#include "..\..\script_component.hpp"

/*
Cross-sensitivity between the dehydration and hypoxia risk accumulators.

Both directions are backed by primary literature:

HYPOXIA AMPLIFIES DEHYDRATION (cap 1.3):
  Acute hypobaric hypoxia causes a rapid diuretic response (reduced
  antidiuretic hormone, renin and aldosterone; increased natriuretic
  hormones) plus increased insensible respiratory water loss from
  hyperventilation (Goldfarb-Rumyantzev & Alpern 2014; Anand 1996,
  IOM "Fluid Metabolism at High Altitudes").  Acute exposure leads to
  hypohydration: total body water and plasma volume fall.  Respiratory
  water loss at altitude adds roughly 1-1.5 L/day over sea-level
  baseline; against a ~3 L/day sweat-driven deficit, that is a
  ~1.3x acceleration of fluid deficit, capped here at 1.3.
  NOTE: the mechanism is INCREASED fluid loss (diuresis + respiration),
  not reduced renal function.  Chronic altitude exposure (>weeks)
  reverses to fluid retention (Anand 1996); this coupling models the
  acute exposure case.

DEHYDRATION AMPLIFIES HYPOXIA IMPACT (cap 1.25):
  Cognitive and psychomotor function degrade at >=2% body-mass water
  loss (Gopinathan et al. 1988, Arch Environ Health 43(1):15-17;
  Lieberman 2007).  Dehydration also reduces plasma volume, increasing
  cardiovascular strain and degrading aerobic capacity at altitude
  (Sawka et al. 2001; Beidleman et al. 2017).  This does NOT accelerate
  AMS onset per se: AMS is associated with fluid RETENTION, not
  dehydration (Loeppky et al. 2005; Swenson 2001), and a 332-subject
  field study found no link between hydration status and AMS incidence
  (Physiol Rep 2021;9:e14809).  The defensible coupling is therefore a
  PERFORMANCE tolerance decrement: at risk=1.0 (~3 L deficit, ~4% body
  mass) the documented cognitive/aerobic degradation reaches roughly
  25%, hence the 1.25 cap.  The earlier "30-50% faster AMS onset"
  figure in the issue spec is NOT supported by the literature and is
  intentionally replaced.

The coupling runs AFTER both accumulators compute their raw risks, so it
reads the current-tick values and writes the amplified results back to the
same variables the consumers read (HUD, ACE3, KAT).  Neither accumulator
reads its own output risk, so writing the amplified value back does not
create a feedback loop.

Settings:
  crossSensitivityEnabled  - toggle the coupling entirely
  crossSensitivityScale    - 0..2 global strength (1 = full literature values)

Amplifiers (anchored to the references above):
  hypoxia amplifier     = 1.0 at 0% dehydration .. 1.25 at 100%
  dehydration amplifier = 1.0 at 0% hypoxia .. 1.3 at 100%
*/

private _enabled = missionNamespace getVariable [QGVAR(crossSensitivityEnabled), true];
if !(_enabled isEqualType true) then { _enabled = true; };
if !(_enabled) exitWith { 0 };

private _scale = missionNamespace getVariable [QGVAR(crossSensitivityScale), 1.0];
if !(_scale isEqualType 0) then { _scale = 1.0; };
if (_scale <= 0) exitWith { 0 };

private _dehydration = missionNamespace getVariable [QGVAR(dehydrationRisk), 0];
if !(_dehydration isEqualType 0) then { _dehydration = 0; };
private _hypoxia = missionNamespace getVariable [QEGVAR(core,currentHypoxiaRisk), 0];
if !(_hypoxia isEqualType 0) then { _hypoxia = 0; };
_dehydration = _dehydration max 0 min 1;
_hypoxia = _hypoxia max 0 min 1;

// Amplifier at full scale: linear from 1.0 (no risk) to the literature cap.
// Interpolate between 1.0 and the cap by the scale setting, so scale 0.5
// gives half the coupling strength.
private _hypAmpFull = linearConversion [0, 1, _dehydration, 1.0, 1.25, true];
private _hypAmp = 1 + (_hypAmpFull - 1) * _scale;

private _dehAmpFull = linearConversion [0, 1, _hypoxia, 1.0, 1.3, true];
private _dehAmp = 1 + (_dehAmpFull - 1) * _scale;

private _effectiveHypoxia = (_hypoxia * _hypAmp) min 1;
private _effectiveDehydration = (_dehydration * _dehAmp) min 1;

missionNamespace setVariable [QGVAR(dehydrationRisk), _effectiveDehydration];
missionNamespace setVariable [QEGVAR(core,currentHypoxiaRisk), _effectiveHypoxia];

[_effectiveDehydration, _effectiveHypoxia]
