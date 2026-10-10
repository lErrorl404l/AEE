#include "..\..\script_component.hpp"

/*
CCT-to-white-point kernel (human-vision model, colour slice).

Pure: no missionNamespace, no GVAR or EGVAR, no engine command.  The base-grade
driver calls this; the kernel converts a correlated colour temperature to the
linear Rec.709 RGB of the daylight or blackbody white point.  The result has the
shape fnc_perceptionIlluminant consumes, so the existing von Kries chain
(fnc_perceptionIlluminant then fnc_perceptionChromaticAdaptation) runs
unchanged.  This is a new SOURCE for the white-balance stage, not a second
white-balance model.

Chain (all SOURCED):
  1. CCT to the CIE 1931 chromaticity (x, y).
     - 4000 K and above: the CIE daylight locus (CIE 15:2004 / S 014-2), valid
       4000 to 25000 K.  Two cubic branches meet at 7000 K.
     - below 4000 K: the Planckian (blackbody) locus, the Kim et al. 2002
       cubic approximation (J. Korean Phys. Soc. 41(6):865-871), valid 1667 to
       4000 K, with its own sub-branch at 2222 K.
  2. (x, y) to XYZ with Y = 1: X = x / y, Z = (1 - x - y) / y.
  3. XYZ to linear Rec.709 RGB with the IEC 61966-2-1 sRGB matrix (D65).
  Each channel floors at 0 (an out-of-gamut colour is not representable).

The engine cannot express a cone matrix and the display is Rec.709, so this is
the display-domain white point.  The issue cites the Tanner Helland 2012
approximation; this kernel uses the CIE loci instead, because the loci are the
standard the approximation fits and are citable by identity.

Per-constant source register:
  daylight locus cubics   SOURCED: CIE 15:2004 / S 014-2.
  Planckian cubics        SOURCED: Kim et al. 2002, J. Korean Phys. Soc.
  XYZ from (x, y)         SOURCED: CIE 15:2004.
  Rec.709 matrix          SOURCED: IEC 61966-2-1 (sRGB), ITU-R BT.709-6.
  CCT band 1667 to 25000  SOURCED: the loci validity bands.
  channel floor 0         UNSOURCED: the out-of-gamut floor.
  y floor 0.0001          UNSOURCED: guards a division by zero.

Arguments:
  0: Number - correlated colour temperature, kelvin

Returns:
  Array - linear Rec.709 white point [r, g, b], each channel 0 and up.
*/

params [
    ["_cct", 6504, [0]]
];

if !(_cct isEqualType 0) then { _cct = 6504; };
_cct = (_cct max 1667) min 25000;

private _x = 0;
private _y = 0;

if (_cct >= 4000) then {
    // CIE daylight locus (CIE 15:2004), two cubic branches at 7000 K.
    if (_cct <= 7000) then {
        _x = (-4.6070e9 / (_cct ^ 3)) + (2.9678e6 / (_cct ^ 2)) + (0.09911e3 / _cct) + 0.244063;
    } else {
        _x = (-2.0064e9 / (_cct ^ 3)) + (1.9018e6 / (_cct ^ 2)) + (0.24748e3 / _cct) + 0.237040;
    };
    _y = (-3.000 * (_x ^ 2)) + (2.870 * _x) - 0.275;
} else {
    // Planckian locus (Kim et al. 2002), 1667 to 4000 K, sub-branch at 2222 K.
    _x = (-0.2661239e9 / (_cct ^ 3)) - (0.2343589e6 / (_cct ^ 2)) + (0.8776956e3 / _cct) + 0.179910;
    if (_cct <= 2222) then {
        _y = (-1.1063814 * (_x ^ 3)) - (1.34811020 * (_x ^ 2)) + (2.18555832 * _x) - 0.20219683;
    } else {
        _y = (-0.9549476 * (_x ^ 3)) - (1.37418593 * (_x ^ 2)) + (2.09137015 * _x) - 0.16748867;
    };
};

private _ysafe = _y max 0.0001;

// XYZ with Y = 1.
private _xx = _x / _ysafe;
private _zz = (1 - _x - _y) / _ysafe;

// XYZ to linear Rec.709 RGB (IEC 61966-2-1 sRGB matrix, D65).
private _r = (3.2406 * _xx) - 1.5372 - (0.4986 * _zz);
private _g = (-0.9689 * _xx) + 1.8758 + (0.0415 * _zz);
private _b = (0.0557 * _xx) - 0.2040 + (1.0570 * _zz);

[(_r max 0), (_g max 0), (_b max 0)]
