#include "..\..\script_component.hpp"

/*
Mesopic-colour kernel (human-vision model, colour slice).

Pure: no missionNamespace, no GVAR or EGVAR, no engine command.  The composition
kernel calls this; the kernel derives the ColorCorrections colorize slot from
the CIE 191:2010 photopic fraction.

Below about 5 cd/m2 the rods take over.  Rods peak near 507 nm and cones near
555 nm, so the world loses colour and shifts blue-green (the Purkinje shift).
CIE 191:2010 gives the photopic fraction m: m=1 is pure photopic, m=0 pure
scotopic.  The kernel uses m to raise the desaturation alpha toward _desatMax
and to move the colorize colour toward the scotopic blue-green hue, scaled by
_purkinjeStrength.  The colorize alpha is the engine desaturation amount
(BIKI Post Process Effects, capture 20240220225631): 0 keeps the original
colour, 1 is black and white times the colorize colour.

Per-constant source register:
  scotopic peak          507 nm.  SOURCED: CIE 1951 and CIE 018:2019.
  photopic fraction m    SOURCED: CIE 191:2010.
  mesopic band           0.005 to 5.0 cd/m2.  SOURCED: CIE 191:2010.  The
                         fraction arrives already computed by the eye model.
  desaturation amplitude 0.3, range 0 to 0.5.  UNSOURCED: operator-tunable.
  Purkinje tint vector   blue-green toward 507 nm.  The tint amplitude is
                         UNSOURCED; the hue direction is SOURCED to CIE 1951.
  alpha clamp            0 to 0.5.  UNSOURCED: the engine desaturates only.

Arguments:
  0: Number - mesopic photopic fraction, 0 scotopic to 1 photopic
  1: Number - maximum desaturation alpha, 0 to 0.5
  2: Number - Purkinje tint strength, 0 to 1

Returns:
  Array - colorize slot [r, g, b, alpha], alpha last, alpha 0 to 0.5.  At
          _mesopicW 1 the return is the identity [1, 1, 1, 0].  At the default
          settings (_desatMax 0, _purkinjeStrength 0) the return is the
          identity for every fraction, so the default path ships no tint.
*/

params [
    ["_mesopicW", 1, [0]],
    ["_desatMax", 0, [0]],
    ["_purkinjeStrength", 0, [0]]
];

private _w = (((_mesopicW max 0) min 1));
private _desat = (((_desatMax max 0) min 0.5));
private _p = (((_purkinjeStrength max 0) min 1));

// Photopic: no desaturation and a neutral colorize colour.
if (_w >= 1) exitWith { [1, 1, 1, 0] };

private _scotopic = (1 - _w);
private _shift = (_scotopic * _p);
private _alpha = (((_desat * _scotopic) max 0) min 0.5);

// Move toward the scotopic blue-green hue (507 nm): reduce red, keep green and
// blue high.  Blue stays above red, which is the Purkinje shift.
private _r = (((1 - (0.5 * _shift)) max 0) min 1);
private _g = 1;
private _b = 1;

[_r, _g, _b, _alpha]
