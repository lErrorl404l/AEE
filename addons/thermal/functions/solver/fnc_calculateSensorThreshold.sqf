#include "..\..\script_component.hpp"
/*
Sensor detection threshold derived from the device NETD (issue #215 family).

WHY THIS EXISTS.  The thermal edge kernel compares a selection's local
contrast against a threshold.  That threshold is a SENSOR property.  It is
the smallest relative radiance contrast the detector can resolve above its
own noise.  It is NOT the display band step.  This kernel derives it from
the mounted device so the edge decision is per-device rather than a fixed
constant.

THE CLOSED FORM.  The band radiance fit in fnc_calculateBandRadiance is
L = A * T^n per segment.  Differentiate it:

    dL/dT = n * A * T^(n-1) = n * L / T

so a temperature difference dT changes the radiance by n * L * dT / T.
Divide by the background radiance L_bg to get the CONTRAST.  The L_bg
cancels:

    contrast = n * dT / T_bg

NETD (Noise Equivalent Temperature Difference) is DEFINED as the
temperature difference that produces a signal equal to the sensor's own
noise, that is a signal-to-noise ratio of 1 (Geminoptics, "NETD"; the AEE
thermal and NVG research dossier states the same).  Reliable detection
sits at a MULTIPLE of that, typically 3 to 10.  That multiple is an
ENGINEERING CHOICE, not a standard, and the record publishes no standard
value for it.  With dT = _snrMultiple * _netdC the threshold is:

    threshold = _snrMultiple * _netdC * n / _tBgK

_tBgK is the background temperature in Kelvin, _netdC the device NETD in
Celsius, and n the local Planck exponent of the DEVICE BAND at the
background temperature, from fnc_planckExponent.  The band is per-device:
the LWIR 8-14 um window and the MWIR 3-5 um window give different slopes
(about 4.7 against 11.3 at a 15 C background), so the two detector classes
no longer share an exponent and the exponent tracks the exact band integral
rather than the retired three-segment power-law fit.

THE SENSOR THRESHOLD AND THE DISPLAY BAND STEP ARE TWO DIFFERENT
QUANTITIES.  At NETD 0.05 C and a multiple of 5, a 15 C background gives
n = 4.7338 (LWIR) and a threshold of

    5 * 0.05 * 4.7338 / 288.15 = 0.004107

ONE DISPLAY QUANTISER IS LIVE.  fnc_applySelectionThermal quantises the
heat tint to 32 levels, so its step is 1 / 31 = 0.03226.  (The 16-band
material set and the 256-material fusion overlay it was followed by are
both removed, so no other quantiser steps in the shipped mod.)

Set that step against the 0.004107 threshold above:

    selection step  0.03226   0.13 of a step, so the step is 7.4 times
                              COARSER than the threshold

The consequence: an edge can be TRUE, in that the sensor resolves the
difference, while the operator sees NO difference, because the quantiser
cannot show it.  The comparison is ILLUSTRATIVE of scale, not an identity:
the threshold is a normalised relative temperature difference, and a step is
a fraction of the AGC window.  The caller must therefore use THIS value for
the sensor decision and keep the quantiser for its own display.  A future
maintainer who raises this threshold to a step would make every device
equally blind, which is the exact error this kernel exists to remove.

Guards, each explicit:
  - A NETD that is not a positive Number is refused with -1.  A zero or
    negative NETD is not a sensor property, and the threshold would be
    meaningless.
  - A signal-to-noise multiple that is not a positive Number is refused
    with -1.
  - A non-finite input is refused with -1.  SQF NaN compares false against
    everything, so max and min cannot clamp it out, and the refusal must
    come before the arithmetic.  This is a real trap in this repository.
  - A background at or below 0 K is refused with -1.  It is the divisor.

Units on every line: _netdC and _tBgC are C and are converted to Kelvin
internally.  The return is a normalised contrast on the same 0..1 scale the
edge kernel uses.

Arguments:
  0: _netdC       (NUMBER) device NETD in C, > 0
  1: _snrMultiple (NUMBER) signal-to-noise multiple for reliable detection,
                  > 0 (ENGINEERING CHOICE, typically 3 to 10)
  2: _tBgC        (NUMBER) background temperature in C
  3: _bandToken   (STRING) device band, "lwir" (default) or "mwir"

Return Value: NUMBER - the sensor detection threshold, a normalised
contrast, or -1 when an input is unusable.
Example: [0.05, 5, 15, "mwir"] call aee_thermal_fnc_calculateSensorThreshold
Public: No
*/

params [
    ["_netdC", 0.05, [0]],
    ["_snrMultiple", 5, [0]],
    ["_tBgC", 15, [0]],
    ["_bandToken", "lwir", [""]]
];

// A non-Number must not reach the arithmetic.  The typed params entries
// enforce this first, and the explicit checks keep the contract local.
if !(_netdC isEqualType 0) exitWith { -1 };
if !(_snrMultiple isEqualType 0) exitWith { -1 };
if !(_tBgC isEqualType 0) exitWith { -1 };

// A non-finite input poisons the result.  SQF NaN compares false against
// everything, so max/min cannot clamp it out.  Refuse before the arithmetic.
if !(finite _netdC) exitWith { -1 };
if !(finite _snrMultiple) exitWith { -1 };
if !(finite _tBgC) exitWith { -1 };

// NETD is a noise sensitivity.  A zero or negative value is not physical,
// and a multiple below one would not be a reliable-detection margin.
if (_netdC <= 0) exitWith { -1 };
if (_snrMultiple <= 0) exitWith { -1 };

// The background is the divisor, in Kelvin.
private _tBgK = _tBgC + KELVIN_OFFSET;
if (_tBgK <= 0) exitWith { -1 };

// The local Planck exponent of the DEVICE BAND at the background
// temperature, from the exact band integral (fnc_planckExponent).  The
// retired three-segment constants were stale and band-blind, so an MWIR
// device reused the LWIR exponent (issue #255).
private _n = [_tBgK, _bandToken] call FUNC(planckExponent);
if (_n <= 0) exitWith { -1 };

_snrMultiple * _netdC * _n / _tBgK
