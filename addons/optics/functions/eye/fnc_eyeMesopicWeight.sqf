#include "..\..\script_component.hpp"

/*
Mesopic weight: the fraction of vision that cones carry.

The eye uses three regimes. At daylight levels the cones carry vision
(photopic). Below about 0.005 cd/m2 the rods carry it (scotopic). Between
the two both work, and the CIE 191:2010 mesopic system blends them through a
photopic fraction m: m=0 is pure scotopic, m=1 is pure photopic.

Band endpoints 0.005 and 5 cd/m2 are TRACED to CIE 191:2010 (restated in
IES TM-12-12). The smoothstep SHAPE between the endpoints is UNSOURCED:
CIE defines the band, not this exact curve.

Arguments:
  0: Number - scene luminance, cd/m2

Returns:
  Number - photopic fraction in [0, 1]. 0 means the rods carry vision,
  1 means the cones carry it.
*/

params [
    ["_lum", 0, [0]],
    ["_lo", 0.005, [0]],
    ["_hi", 5, [0]]
];

// The endpoints default to the TRACED values and the driver passes the
// AEE Optics > Eye Adaptation settings, so the band is operator-tunable.

if (_lum <= _lo) exitWith { 0 };
if (_lum >= _hi) exitWith { 1 };

private _t = ((log _lum) - (log _lo)) / ((log _hi) - (log _lo));
private _w = _t * _t * (3 - (2 * _t));

_w
