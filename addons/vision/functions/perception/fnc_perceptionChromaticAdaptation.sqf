#include "..\..\script_component.hpp"

/*
Chromatic-adaptation kernel (human-vision model, colour slice).

Pure: no missionNamespace, no GVAR or EGVAR, no engine command.  The composition
kernel calls this; the kernel derives the ColorCorrections blend slot from the
scene illuminant and the display white.

The eye adapts to the illuminant with the von Kries coefficient law, a diagonal
gain in cone space (von Kries 1902).  The modern form is CAT16 (Li et al. 2017,
DOI 10.1002/col.22131); the earlier CAT02 matrix is CIE 159:2004.  The engine
has no matrix and no cone space, so this kernel approximates the diagonal gain
with a small blend toward the complementary tint in the display domain:
clamp(2 - illuminantNormalised, 0, 1).  A blue cast therefore blends warm and a
warm cast blends cool.  The diagonal von Kries gain 1/illuminantNormalised sets
the colour-error magnitude that scales the blend alpha.

The degree of adaptation D is partial.  CIECAM02 defines
D = F * (1 - (1/3.6) * exp((-LA - 42) / 92)); F is 0.8 dim, 0.9 average, 1.0
dark (CIE 159:2004).  The caller passes D; the default 0.9 is the average
surround.  The engine cannot express a matrix, so the display-RGB diagonal and
the blend cap are the approximation; both are UNSOURCED.

The white target is the display white D65 at x 0.3127, y 0.3290 (CIE 15:2004
and ITU-R BT.709-6).  The illuminant arrives normalised to unit luminance by
fnc_perceptionIlluminant.

Per-constant source register:
  von Kries diagonal gain  SOURCED: von Kries 1902; CAT16 in Li et al. 2017.
  adaptation degree D      SOURCED: CIE 159:2004.  Default F 0.9, range 0.8-1.0.
  D65 white                SOURCED: CIE 15:2004 and ITU-R BT.709-6.
  display-RGB diagonal     UNSOURCED: the engine has no matrix.
  blend cap               0.25, UNSOURCED: a blend toward a solid colour washes
                          the image out.
  channel floor           EPSILON, UNSOURCED: guards a division by zero.

Arguments:
  0: Array  - unit-luminance illuminant colour (fnc_perceptionIlluminant)
  1: Number - adaptation degree D, 0 to 1
  2: Number - blend cap, 0 to 0.25

Returns:
  Array - blend slot [r, g, b, alpha], alpha 0 to the cap.  At D 0 the return is
          the identity [1, 1, 1, 0].
*/

params [
    ["_illuminant", [1, 1, 1], [[]]],
    ["_degree", 0.9, [0]],
    ["_cap", 0.25, [0]]
];

private _neutral = [1, 1, 1, 0];

private _d = (((_degree max 0) min 1));
private _c = (((_cap max 0) min 0.25));
if (_d <= 0) exitWith { _neutral };

if (!(_illuminant isEqualType [])) exitWith { _neutral };
if ((count _illuminant) != 3) exitWith { _neutral };

private _ok = true;
if (!((_illuminant select 0) isEqualType 0)) then { _ok = false; };
if (!((_illuminant select 1) isEqualType 0)) then { _ok = false; };
if (!((_illuminant select 2) isEqualType 0)) then { _ok = false; };
if (!_ok) exitWith { _neutral };

private _ir = (_illuminant select 0) max EPSILON;
private _ig = (_illuminant select 1) max EPSILON;
private _ib = (_illuminant select 2) max EPSILON;

// The complementary tint in the display domain (UNSOURCED approximation).
private _compR = (((2 - _ir) max 0) min 1);
private _compG = (((2 - _ig) max 0) min 1);
private _compB = (((2 - _ib) max 0) min 1);

// Blend the tint toward the identity 1 by the degree of adaptation.
private _blendR = 1 + (_d * (_compR - 1));
private _blendG = 1 + (_d * (_compG - 1));
private _blendB = 1 + (_d * (_compB - 1));

// The diagonal von Kries gain 1/illuminant sets the colour-error magnitude.
private _gr = 1 / _ir;
private _gg = 1 / _ig;
private _gb = 1 / _ib;
private _err = (((abs (_gr - 1)) max (abs (_gg - 1))) max (abs (_gb - 1)));
private _mag = ((_err max 0) min 1);

private _alpha = (((_c * _d * _mag) max 0) min _c);

[_blendR, _blendG, _blendB, _alpha]
