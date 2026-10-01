#include "..\..\script_component.hpp"
/*
Thermal edge decision from a selection's band radiance and a LOCAL background.

WHY THIS FUNCTION EXISTS.  A thermal EDGE is a LOCAL contrast question.  A
real FLIR resolves a target when the target signal stands above the
background in the SAME LOCAL NEIGHBOURHOOD by more than the sensor can
resolve.  It is NOT a scene-window question.  A scene-adaptive threshold
moves with the scene, and sensitivity belongs to the SENSOR and stays
fixed, so normalising a decision against the AGC window inverts the
physics: a large uniform scene raises the global maximum and HIDES a local
target that a local-background test would find.  The caller computes the
local background from the object's OTHER selections and passes it in.
This kernel takes that background as an argument and does NOT read the AGC
window (QGVAR(agcRadMin) / QGVAR(agcRadMax)) at all.

THE CRITERION.  Relative contrast of the signal above its own local
background, clamped to the display scale, compared with a threshold:

    contrast = ((signal - background) / background) clamped to 0..1
    edge     = contrast >= threshold

A signal at its background reads contrast 0 and is not an edge.  A signal
below its background clamps to 0 and is not an edge.  A signal well above
its background reads toward 1 and is an edge.

THE THRESHOLD IS SENSOR-DERIVED.  The threshold is the device's detection
sensitivity, derived by fnc_calculateSensorThreshold from the mounted
device's NETD, the signal-to-noise multiple and the background temperature.
NETD (Noise Equivalent Temperature Difference) is DEFINED as the
temperature difference that produces a signal equal to the sensor's own
noise, that is a signal-to-noise ratio of 1 (Geminoptics, "NETD"; the AEE
thermal and NVG research dossier states the same).  Reliable detection sits
at a MULTIPLE of that, typically 3 to 10.  That multiple is an ENGINEERING
CHOICE, not a standard, and the record publishes no standard value for it.
The shipped caller passes the derived value.  The declared default below is
the uncooled 0.05 C reference device at a multiple of 5 and a 15 C
background, which is 5 * 0.05 * 5.0121 / 288.15 = 0.004349.

THE SENSOR THRESHOLD AND THE DISPLAY BAND STEP ARE TWO DIFFERENT
QUANTITIES, AND THEY MUST NOT BE CONFLATED.  One display quantiser is live:
the selection path, fnc_applySelectionThermal, quantises the heat tint to
32 levels, so its step is 1 / 31 = 0.03226.  (The 16-band step and the
256-material fusion overlay that followed it are both removed, so no other
quantiser steps in the shipped mod.)

The sensor threshold above is 0.004349.  Against the selection step it is
0.13 of a step, so an edge can be TRUE, in that the sensor resolves the
difference, while the operator sees NO difference.  The comparison is
ILLUSTRATIVE of scale, not an identity: the threshold is a normalised
relative temperature difference, and a step is a fraction of the AGC
window, so the two numbers are not commensurable and neither may be derived
from the other.

This kernel therefore clamps the threshold to the 0..1 contrast scale ONLY.
It does NOT floor the threshold at a display step, on either path, because
a band floor would make every device equally blind and would undo the
per-device decision.  That reason does not depend on the band depth.  A
future maintainer must not "fix" this by raising the threshold to a step.

SPATIAL RESOLUTION IS A SEPARATE AXIS, AND IT IS DELIBERATELY NOT
IMPLEMENTED.  Johnson criteria give detection at about 1 line pair, often
taken as 2 pixels across the critical dimension, recognition at about 4 and
identification at about 6.4, at roughly 50 percent probability, and STANAG
4347 Ed. 1 (18 July 1995) defines the nominal static range in those terms.
This kernel decides CONTRAST ONLY.  A selection can be a strong contrast
edge and still be too small to resolve, so contrast detection is NECESSARY
AND NOT SUFFICIENT.  The system figure of merit that joins NETD to spatial
frequency is MRTD.  No range and no resolution limit is computed here,
because MRTD needs a spatial-frequency curve this repository does not hold,
and inventing a range would be the most misleading thing this feature could
do.

Guards, each explicit:
  - A background that is not a positive Number is refused with [false, -1].
    It is the divisor, and a non-positive divisor is undefined, so it is
    refused rather than divided by.
  - A signal that is not a finite Number is refused with [false, -1].  SQF
    NaN compares false against everything, so max and min cannot clamp it
    out; the refusal must come before the arithmetic.  This is a real trap
    in this repository.
  - A threshold that is not a Number is refused with [false, -1].  A Number
    threshold outside the scale is clamped to the 0..1 contrast scale,
    never floored at one band and never extrapolated.
  - The returned contrast is clamped to 0..1, never extrapolated.

Units on every line: _signal and _background are W/m2/sr.  _threshold is a
normalised contrast on the 0..1 scale.  It is a SENSOR quantity, not a
display band step.

Arguments:
  0: _signal     (NUMBER) selection band radiance, W/m2/sr
  1: _background (NUMBER) local background band radiance, W/m2/sr, > 0
  2: _threshold  (NUMBER) sensor-derived minimum resolvable contrast, 0..1
                 (default: the uncooled 0.05 C reference, 0.004349)

Return Value: ARRAY [edge (BOOL), contrast (NUMBER)].  The contrast is 0..1.
On an unusable input the kernel returns the refusal [false, -1].
Example: [52.4, 41.0] call aee_thermal_fnc_evaluateThermalEdge
Public: No
*/

params [
    ["_signal", 0, [0]],
    ["_background", 0, [0]],
    ["_threshold", 0.004349, [0]]
];

// A non-Number must not reach the arithmetic.  The typed params entries
// enforce this first; the explicit checks keep the contract local, because a
// caller can pass a value the type list widened.
if !(_signal isEqualType 0) exitWith { [false, -1] };
if !(_background isEqualType 0) exitWith { [false, -1] };
if !(_threshold isEqualType 0) exitWith { [false, -1] };

// A non-finite input poisons the contrast.  SQF NaN compares false against
// everything, so max/min cannot clamp it out; refuse before the arithmetic.
if !(finite _signal) exitWith { [false, -1] };
if !(finite _background) exitWith { [false, -1] };
if !(finite _threshold) exitWith { [false, -1] };

// The background is the divisor.  A zero or negative background has no
// contrast to resolve, so it is refused rather than divided by.
if (_background <= 0) exitWith { [false, -1] };

// The relative contrast, clamped to the display scale.  A signal at or below
// the background reads 0; a signal well above reads toward 1.
private _contrast = ((_signal - _background) / _background) max 0 min 1;
if !(finite _contrast) exitWith { [false, -1] };

// The threshold is a SENSOR quantity, derived per device by
// fnc_calculateSensorThreshold.  Clamp it to the 0..1 contrast scale only.
// One display step is live: the selection path, fnc_applySelectionThermal,
// steps 1 / 31 over 32 tint levels.  It is a DISPLAY quantity.  The 0.004349
// threshold is 0.13 of that step.  The comparison is illustrative of scale,
// not an identity, so neither number is derived from the other.  The step is
// not a floor, because a band floor would hide the per-device sensitivity
// and make every device equally blind.  The band floor is deliberately NOT
// applied here.
private _thresholdClamped = _threshold max 0 min 1;

private _edge = _contrast >= _thresholdClamped;

[_edge, _contrast]
