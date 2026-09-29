#include "..\..\script_component.hpp"
/*
Johnson-criteria spatial resolution for a thermal target (issue #196 family).

WHY THIS EXISTS.  fnc_evaluateThermalEdge decides a CONTRAST edge and says so
in its own header: "a selection can be a strong contrast edge and still be
too small to resolve, so contrast detection is NECESSARY AND NOT
SUFFICIENT".  Until now that sentence had no implementation.  This kernel is
the missing spatial half.  An edge that exists but is smaller than a few
detector pixels is not a resolvable target, and the fusion overlay must be
able to report it UNRESOLVED.

THE INPUTS, AND WHERE THEY COME FROM.  Detector resolution is resolved per
device by fnc_getThermalDeviceProperties (resX).  The angular size of one
pixel (the instantaneous field of view) is the horizontal field of view
divided by the pixel count, and the field of view follows the published
relation in docs/wiki/research/sensor-device-library.md, "FOV falls as
magnification rises (~24/mag deg for the 4x-class optic)".  The target's
angular size is the caller's: the caller divides the target's critical
dimension by its range (radians).  This kernel is pure arithmetic over
scalars, so the dedicated server can measure it headless.

THE CRITERIA (STANAG 4347 Ed. 1, 18 July 1995, nominal static range defined
at 50 percent probability; Johnson 1958):
  detection        about 1.0 line pair, taken as 2 pixels across the
                   critical dimension
  recognition      about 4.0 line pairs, that is 8 pixels
  identification   about 6.4 line pairs, that is 12.8 pixels
A line pair is one dark and one light bar, so one line pair spans 2 pixels.
The kernel reports the Johnson LEVEL the geometry supports: 0 unresolved,
1 detection, 2 recognition, 3 identification.

WHAT THIS IS NOT.  It does NOT compute a range, a probability of detection or
an MRTD curve, and it deliberately invents none.  MRTD joins NETD to spatial
frequency into one curve; the repository holds no published MRTD curve for
these devices, so no MRTD value is produced here (see the header of
fnc_evaluateThermalEdge for the same limit stated there).  The caller keeps
the contrast decision separate, and this kernel only refuses geometries too
small to resolve.

THE 24/mag RELATION IS A DECLARED APPROXIMATION.  It is the published
4x-class figure the repository already holds.  A caller with a measured FOV
would be entitled to bypass it; none is available per device here, so the
relation is used and named as an approximation, not as a measurement.

Guards, each explicit:
  - A non-Number or non-finite input is refused with [false, 0, 0].  SQF NaN
    compares false against everything, so max and min cannot clamp it out;
    the refusal must come before the arithmetic.
  - A target angle below zero, a non-positive resolution, or a magnification
    below 1 is refused with [false, 0, 0].  Magnification below 1 would make
    the derived field of view exceed the 24-degree reference and is not a
    real optic.
  - Magnification is clamped to at least 1 so the divisor is never small.

Units on every line: _targetAngleRad is radians, _resX is pixels, _mag is a
ratio.  The return is [resolvable (BOOL), level (NUMBER 0..3),
linePairs (NUMBER)].

Arguments:
  0: _targetAngleRad (NUMBER) angular size of the target critical dimension,
                     radians, >= 0
  1: _resX          (NUMBER) detector horizontal resolution, pixels, > 0
  2: _mag           (NUMBER) optic magnification, ratio, >= 1

Return Value: ARRAY [resolvable (BOOL), level (NUMBER), linePairs (NUMBER)].
Example: [0.0016667, 640, 4] call aee_thermal_fnc_resolveThermalTarget
Public: No
*/

params [
    ["_targetAngleRad", 0, [0]],
    ["_resX", 640, [0]],
    ["_mag", 1, [0]]
];

if !(_targetAngleRad isEqualType 0) exitWith { [false, 0, 0] };
if !(_resX isEqualType 0) exitWith { [false, 0, 0] };
if !(_mag isEqualType 0) exitWith { [false, 0, 0] };

if !(finite _targetAngleRad) exitWith { [false, 0, 0] };
if !(finite _resX) exitWith { [false, 0, 0] };
if !(finite _mag) exitWith { [false, 0, 0] };

// An angle below zero is not a target, a non-positive detector has no
// pixels, and a magnification below 1 is not an optic.
if (_targetAngleRad < 0) exitWith { [false, 0, 0] };
if (_resX <= 0) exitWith { [false, 0, 0] };
if (_mag < 1) exitWith { [false, 0, 0] };

// The published FOV relation the repository already holds, then the
// angular size of one detector pixel.
private _fovDeg = 24 / _mag;
private _ifovDeg = _fovDeg / _resX;

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

[_level >= 1, _level, _linePairs]
