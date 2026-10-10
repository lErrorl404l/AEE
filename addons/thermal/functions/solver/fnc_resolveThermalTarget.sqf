#include "..\..\script_component.hpp"
/*
Johnson-criteria spatial resolution for a thermal target (issue #196 family).

WHY THIS EXISTS.  fnc_evaluateThermalEdge decides a CONTRAST edge and says so
in its own header: "a selection can be a strong contrast edge and still be
too small to resolve, so contrast detection is NECESSARY AND NOT
SUFFICIENT".  This kernel is the missing spatial half.  It reports the
Johnson LEVEL the geometry supports and, for a target at or below one pixel,
the signal-to-noise margin that still makes it detectable.

THE CRITERIA (STANAG 4347 Ed. 1, 18 July 1995, nominal static range defined
at 50 percent probability; Johnson 1958):
  detection        about 1.0 line pair, taken as 2 pixels across the
                   critical dimension
  recognition      about 4.0 line pairs, that is 8 pixels
  identification   about 6.4 line pairs, that is 12.8 pixels
A line pair is one dark and one light bar, so one line pair spans 2 pixels.
The kernel reports 0 unresolved, 1 detection, 2 recognition, 3 identification.

THE SUB-PIXEL SNR TERM.  A target smaller than one detector pixel still
delivers detectable energy: its energy concentrates in the one pixel it
covers, so detection becomes a signal-to-noise question, not a cycle-count
question.  The per-pixel signal-to-noise ratio falls LINEARLY with the filled
area fraction (A_target / A_IFOV), NOT as its square root, because a
sub-pixel target illuminates one pixel and there is no noise averaging over
its own area (US Army Night Vision Laboratory, ECOM-7043 / ADA011212, "Static
Performance Model for Thermal Viewing Systems", April 1975, Eq. 29).  The
detection margin is SNR >= 2.8, the 50 percent detection point of the
probability-SNR table (ADA011212 Table 6, from Rosell and Wilson,
AFAL-TR-74-104, 1974), chosen to match the Johnson convention of 50 percent
probability.  The model default threshold in the same source is 2.25; 2.8 is
used because it is the tabulated 50 percent point.  The extended-source SNR
at full-pixel fill is contrast / (netdC * n / tBgK), the same relative
radiance-contrast relation the sensor threshold kernel uses
(fnc_calculateSensorThreshold).

HOW IT BEHAVES AT AND BELOW ONE PIXEL.  At one pixel the fill fraction is 1,
so the full-pixel SNR applies.  Below one pixel the fill is the square of the
pixel span, and the margin is reached only with sufficient contrast.  Between
one pixel and one line pair the spatial term is NOT applied: the point-source
relation is derived for a target smaller than one IFOV, and the kernel will
not force it, so that band stays unresolved.  That is the defensible bound.
A caller that supplies no contrast (the default 0) gets the geometry-only
decision, because no signal-to-noise claim can be made without a contrast.

WHAT THIS IS NOT.  It does NOT compute a range, a probability of detection or
an MRTD curve, and it deliberately invents none.  MRTD joins NETD to spatial
frequency into one curve; the repository holds no published MRTD curve for
these devices, so no MRTD value is produced here (see the header of
fnc_evaluateThermalEdge for the same limit stated there).

THE FOV PROVENANCE.  The horizontal field of view of the THERMAL CHANNEL is
lens-dependent (sensor-device-library.md: "FOV is lens-dependent - encode per
lens") and is a different optic from the day scope.  A caller should pass the
thermal lens FOV as _fovDeg.  The repository holds no per-lens thermal FOV,
so when _fovDeg is not supplied the kernel falls back to FOV = 24 / _mag.
That relation is the published DAY-OPTIC 4x-class figure the repository holds
(sensor-device-library.md L140); the measured 4x day-optic FOVs it lists span
6 to 10 degrees (L147-159), so the fallback sits at the narrow end and is a
DECLARED APPROXIMATION of the thermal lens, not a measurement.  A caller with
the device's own FOV must pass it.

Guards, each explicit:
  - A non-Number or non-finite input is refused with [false, 0, 0].  SQF NaN
    compares false against everything, so max and min cannot clamp it out;
    the refusal must come before the arithmetic.
  - A target angle below zero, a non-positive resolution, or a negative FOV
    is refused with [false, 0, 0].  A magnification below 1 is refused only
    when the 24/mag fallback is used, because a supplied thermal FOV does not
    depend on the day optic.
  - A non-positive NETD or a background at or below absolute zero is refused
    with [false, 0, 0]: the SNR term cannot be evaluated.

Units on every line: _targetAngleRad is radians, _resX is pixels, _fovDeg and
_tBgC are degrees Celsius, _mag is a ratio, _netdC is Celsius, _contrast is a
normalised relative radiance contrast on 0..1.

Arguments:
  0: _targetAngleRad (NUMBER) angular size of the target critical dimension,
                     radians, >= 0
  1: _resX          (NUMBER) detector horizontal resolution, pixels, > 0
  2: _mag           (NUMBER) day-optic magnification, ratio, >= 1 (fallback)
  3: _fovDeg        (NUMBER) thermal channel horizontal FOV, degrees;
                     0 = derive from _mag via 24 / _mag
  4: _netdC         (NUMBER) device NETD in C, > 0
  5: _contrast      (NUMBER) normalised target radiance contrast, 0..1
  6: _tBgC          (NUMBER) background temperature in C

Return Value: ARRAY [resolvable (BOOL), level (NUMBER), linePairs (NUMBER)].
Example: [0.0016667, 640, 4] call aee_thermal_fnc_resolveThermalTarget
Public: No
*/

params [
    ["_targetAngleRad", 0, [0]],
    ["_resX", 640, [0]],
    ["_mag", 1, [0]],
    ["_fovDeg", 0, [0]],
    ["_netdC", 0.05, [0]],
    ["_contrast", 0, [0]],
    ["_tBgC", 15, [0]]
];

if !(_targetAngleRad isEqualType 0) exitWith { [false, 0, 0] };
if !(_resX isEqualType 0) exitWith { [false, 0, 0] };
if !(_mag isEqualType 0) exitWith { [false, 0, 0] };
if !(_fovDeg isEqualType 0) exitWith { [false, 0, 0] };
if !(_netdC isEqualType 0) exitWith { [false, 0, 0] };
if !(_contrast isEqualType 0) exitWith { [false, 0, 0] };
if !(_tBgC isEqualType 0) exitWith { [false, 0, 0] };

if !(finite _targetAngleRad) exitWith { [false, 0, 0] };
if !(finite _resX) exitWith { [false, 0, 0] };
if !(finite _mag) exitWith { [false, 0, 0] };
if !(finite _fovDeg) exitWith { [false, 0, 0] };
if !(finite _netdC) exitWith { [false, 0, 0] };
if !(finite _contrast) exitWith { [false, 0, 0] };
if !(finite _tBgC) exitWith { [false, 0, 0] };

// An angle below zero is not a target, a non-positive detector has no
// pixels, and a negative field is not an optic.
if (_targetAngleRad < 0) exitWith { [false, 0, 0] };
if (_resX <= 0) exitWith { [false, 0, 0] };
if (_fovDeg < 0) exitWith { [false, 0, 0] };
// The 24/mag fallback needs a real day-optic magnification; a supplied
// thermal FOV does not depend on it.
if (_fovDeg == 0 && _mag < 1) exitWith { [false, 0, 0] };
if (_netdC <= 0) exitWith { [false, 0, 0] };
if (_tBgC <= -KELVIN_OFFSET) exitWith { [false, 0, 0] };
_contrast = (_contrast max 0) min 1;

// The thermal channel's own lens FOV when supplied, otherwise the published
// day-optic relation as a declared approximation.
private _horFovDeg = if (_fovDeg > 0) then { _fovDeg } else { 24 / _mag };
private _ifovDeg = _horFovDeg / _resX;

// The target spans this many pixels across its critical dimension.  A line
// pair is a pair of pixels, so the line-pair count is half the pixel count.
private _targetDeg = _targetAngleRad * (180 / pi);
private _pixels = _targetDeg / _ifovDeg;
private _linePairs = _pixels / 2;

// Johnson task levels at about 50 percent probability, STANAG 4347 Ed. 1.
private _level = 0;
if (_linePairs >= 1.0) then { _level = 1; };
if (_linePairs >= 4.0) then { _level = 2; };
if (_linePairs >= 6.4) then { _level = 3; };

// Sub-line-pair: Johnson geometry alone refuses, but a single-pixel or
// sub-pixel target can still be detected by signal-to-noise.  The fill
// fraction is the pixel span squared below one pixel and 1 above it (a
// target that fills a whole pixel has no concentration left to lose).
if (_level < 1) then {
    private _fill = (_pixels min 1) ^ 2;
    private _tBgK = _tBgC + KELVIN_OFFSET;
    private _n = 5.0121;
    if (_tBgK > 290) then { _n = 4.4580; };
    if (_tBgK > 330) then { _n = 3.7101; };
    private _snrFull = _contrast * _tBgK / (_n * _netdC);
    private _snrSub = _snrFull * _fill;
    if (_snrSub >= 2.8) then { _level = 1; };
};

[_level >= 1, _level, _linePairs]
