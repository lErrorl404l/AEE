#include "..\..\script_component.hpp"

/*
Tone-response kernel (human-vision model).

Pure: no missionNamespace, no GVAR or EGVAR, no engine command.  The base-grade
driver calls this; the kernel maps the adapted scene luminance to the display
brightness, contrast and black point the ColorCorrections effect consumes.

Model.  The retina compresses a wide luminance range into a narrow response.
The standard form is the Naka-Rushton equation, R = Rmax times I to the n,
divided by the sum of I to the n and sigma to the n (Naka and Rushton 1966,
J Physiol, DOI 10.1113/jphysiol.1966.sp008003).  Above the photoreceptors the
percept follows the CIE 1976 lightness function L* (CIE 15:2004 and ISO
11664-4).  The kernel evaluates both at the adapted operating point, takes the
first-order tangent, and folds it into the affine ColorCorrections can express.
Stevens 1957 gives the brightness power law near 0.33 for reference.

The engine contrast is linear, so this is a stand-in for a curve, not a curve.
The exact Naka-Rushton exponent and sigma are UNSOURCED and operator-tunable.

Per-constant source register (UNSOURCED values are marked beside the clamp):
  Naka-Rushton exponent n   0.7, range 0.5 to 1.0.  Form SOURCED (Naka and
                            Rushton 1966).  The exact value is UNSOURCED.
  Naka-Rushton sigma        0.18, the mid-grey reflectance.  Form SOURCED.
                            The exact value is UNSOURCED (photographic
                            convention, not a CIE constant).
  CIE L* exponent           1/3.  SOURCED: CIE 15:2004 and ISO 11664-4.
  CIE L* threshold delta    6/29, delta cubed 0.008856.  SOURCED: CIE 15:2004.
  Stevens brightness exp    0.33.  SOURCED: Stevens 1957, secondary table.
  contrast                  0.8 to 1.6.  UNSOURCED: matches the legacy
                            base-grade clamp.
  offset                    -0.05 to 0.05.  UNSOURCED: BIKI says the offset
                            range is 0 and up; negative is proven in
                            community code.
  brightness                0.7 to 1.3.  BIKI ColorCorrections brightness,
                            0 black, 1 unchanged, 2 white.

Arguments:
  0: Number - adapted scene luminance, cd/m2
  1: Number - reference luminance for the operating point, cd/m2
  2: Number - model strength, 0 to 1 (0 is the identity)
  3: Number - contrast scale, the calibration gain

Returns:
  Array - [brightness, contrast, offset]
*/

params [
    ["_adaptedLum", 1, [0]],
    ["_refLum", 100, [0]],
    ["_strength", 1, [0]],
    ["_contrastScale", 1, [0]]
];

private _s = ((_strength max 0) min 1);
private _scale = ((_contrastScale max 0.5) min 1.5);
private _lum = (_adaptedLum max 0.00001);
private _ref = (_refLum max 0.00001);

// Stage 1: the Naka-Rushton retinal response at the operating point.  The
// sigma is measured in the reference-relative unit, so 0.18 is mid grey.
private _n = 0.7;
private _sigma = 0.18;
private _x = _lum / _ref;
private _xn = _x ^ _n;
private _sn = _sigma ^ _n;
private _r = _xn / (_xn + _sn);

// Stage 2: the CIE 1976 L* percept, normalised to 0 to 1.
private _delta = 6 / 29;
private _deltaCubed = _delta ^ 3;
private _lstar = 0;
if (_r > _deltaCubed) then {
    _lstar = ((116 * (_r ^ (1 / 3))) - 16) / 100;
} else {
    _lstar = (_r * ((29 / 3) ^ 3)) / 100;
};

// The reference percept, the tangent intercept the display black point
// offsets from.
private _refR = 1 / (1 + _sn);
private _refLstar = 0;
if (_refR > _deltaCubed) then {
    _refLstar = ((116 * (_refR ^ (1 / 3))) - 16) / 100;
} else {
    _refLstar = (_refR * ((29 / 3) ^ 3)) / 100;
};

// Stage 3: the first-order tangent.  The display contrast is the reciprocal of
// the perceptual log-slope, smallest at the reference adaptation, and rises as
// the operating point leaves it.  The affine is a stand-in for the curve.
private _shift = (log _lum) - (log _ref);
private _mag = abs _shift;
private _response = _mag / (_mag + 1);

private _contrast = 1 + (_scale * 0.6 * _s * _response);
private _offset = 0.1 * _s * (_refLstar - _lstar);
private _brightness = 1 + (0.3 * _s * ((0 - _shift) / (_mag + 1)));

_contrast = ((_contrast max 0.8) min 1.6);
_offset = ((_offset max -0.05) min 0.05);
_brightness = ((_brightness max 0.7) min 1.3);

[_brightness, _contrast, _offset]
