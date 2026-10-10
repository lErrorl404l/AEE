#include "..\..\script_component.hpp"

/*
Illuminant kernel (human-vision model, colour slice).

Pure: no missionNamespace, no GVAR or EGVAR, no engine command.  The composition
kernel calls this; the kernel normalises the engine ambient colour to unit
luminance so the white-balance stage can compare it with the display white.

The engine ambient colour is the ambientLightColor element of getLightingAt
(BIKI getLightingAt, capture 20250120023422): a three-value RGB colour with no
fixed unit.  The kernel divides each channel by the Rec.709 luma
(REC709_LUMA_R, REC709_LUMA_G, REC709_LUMA_B), so a neutral grey returns [1,1,1] and a tinted colour
exposes its cast.  A black, malformed or near-black input returns [1,1,1], which
asks for no adaptation.  Each channel clamps to 0.5 to 2 to bound the tint.

The white target is the display white D65 (CIE 15:2004 and ITU-R BT.709-6).  The
partial von Kries adaptation itself is in fnc_perceptionChromaticAdaptation.

Per-constant source register:
  Rec.709 luma weights   REC709_LUMA_R, REC709_LUMA_G, REC709_LUMA_B.  SOURCED: ITU-R BT.709-6.
  luma floor             EPSILON.  UNSOURCED: guards a division by zero on a
                         black or near-black ambient colour.
  channel clamp          0.5 to 2.  UNSOURCED: bounds the tint magnitude.
  D65 white              x 0.3127, y 0.3290.  SOURCED: CIE 15:2004.

Arguments:
  0: Array - engine ambient colour, three numbers

Returns:
  Array - unit-luminance illuminant colour, each channel in 0.5 to 2, or
          [1,1,1] when the input is black, malformed or below the floor.
*/

params [
    ["_ambientColor", [1, 1, 1], [[]]]
];

private _neutral = [1, 1, 1];

if (!(_ambientColor isEqualType [])) exitWith { _neutral };
if ((count _ambientColor) != 3) exitWith { _neutral };

private _ok = true;
if (!((_ambientColor select 0) isEqualType 0)) then { _ok = false; };
if (!((_ambientColor select 1) isEqualType 0)) then { _ok = false; };
if (!((_ambientColor select 2) isEqualType 0)) then { _ok = false; };
if (!_ok) exitWith { _neutral };

private _r = _ambientColor select 0;
private _g = _ambientColor select 1;
private _b = _ambientColor select 2;

// Rec.709 luma (ITU-R BT.709-6).
private _luma = (REC709_LUMA_R * _r) + (REC709_LUMA_G * _g) + (REC709_LUMA_B * _b);
if (_luma <= EPSILON) exitWith { _neutral };

_r = (((_r / _luma) max 0.5) min 2);
_g = (((_g / _luma) max 0.5) min 2);
_b = (((_b / _luma) max 0.5) min 2);

[_r, _g, _b]
