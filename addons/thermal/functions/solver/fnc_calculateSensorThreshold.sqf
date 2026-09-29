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
Celsius, and n the Planck exponent of the segment that holds the
background.  The exponent is selected the same way fnc_calculateBandRadiance
selects its segment: night 250-290 K, n = 5.0121; day 290-330 K, n = 4.4580;
hot 330-450 K, n = 3.7101.

THE SENSOR THRESHOLD AND THE DISPLAY BAND STEP ARE TWO DIFFERENT
QUANTITIES.  At NETD 0.05 C and a multiple of 5, a 15 C background gives
n = 5.0121 and a threshold of

    5 * 0.05 * 5.0121 / 288.15 = 0.004349

AEE's display quantises to 16 bands, so one band is 1 / 16 = 0.0625.  The
sensor threshold is about fourteen times finer than one display band.  That
relationship is physically correct: a real sensor resolves differences far
smaller than the display can show.  The consequence is that an edge can be
TRUE, in that the sensor resolves the difference, while the operator sees
NO difference, because the 16-step quantiser cannot show it.  The caller
must therefore use THIS value for the sensor decision and keep the band
step for the display.  A future maintainer who raises this threshold to one
band would make every device equally blind, which is the exact error this
kernel exists to remove.

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

Return Value: NUMBER - the sensor detection threshold, a normalised
contrast, or -1 when an input is unusable.
Example: [0.05, 5, 15] call aee_thermal_fnc_calculateSensorThreshold
Public: No
*/

params [
    ["_netdC", 0.05, [0]],
    ["_snrMultiple", 5, [0]],
    ["_tBgC", 15, [0]]
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
private _tBgK = _tBgC + 273.15;
if (_tBgK <= 0) exitWith { -1 };

// The Planck exponent of the segment holding the background.  The same
// boundaries and exponents as fnc_calculateBandRadiance: night 250-290 K,
// day 290-330 K, hot 330-450 K.  The fit clamps its temperature to
// 240..460 K before selecting, which cannot change the selected segment
// for a real background, so the boundaries alone are enough.
private _n = 5.0121;
if (_tBgK > 290) then { _n = 4.4580; };
if (_tBgK > 330) then { _n = 3.7101; };

_snrMultiple * _netdC * _n / _tBgK
