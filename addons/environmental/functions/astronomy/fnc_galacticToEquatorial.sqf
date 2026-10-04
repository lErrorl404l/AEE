#include "..\..\script_component.hpp"

/*
Galactic coordinates to J2000 equatorial coordinates.

The Milky Way band is defined in galactic longitude l and latitude b and must
be drawn in the same equatorial frame the star catalogue uses, so the renderer
needs this transform.  The frame follows the IAU 1958 galactic system: the
equatorial J2000 coordinates of the galactic north pole and the galactic
longitude of the north celestial pole.

Standard reverse transform (Wikipedia "Galactic coordinate system", sourced
from Blaauw et al. 1960):

    sin(dec) = sin(deNgp) sin(b) + cos(deNgp) cos(b) cos(lNcp - l)
    y        = cos(b) sin(lNcp - l)
    x        = cos(deNgp) sin(b) - sin(deNgp) cos(b) cos(lNcp - l)
    ra       = raNgp + atan2(y, x)

SQF trigonometric functions take degrees, so the angles feed them directly.
The kernel is pure: it reads no missionNamespace, GVAR or engine command, so
tools/tests/sqf_lite.py can execute it.

Arguments:
  0: Number - galactic longitude, degrees
  1: Number - galactic latitude, degrees

Returns:
  Array [raDeg, decDeg] - J2000 right ascension in [0, 360) and declination.
*/

params [
    ["_lDeg", 0, [0]],
    ["_bDeg", 0, [0]]
];

// IAU 1958 galactic frame constants (Blaauw et al. 1960).
private _raNgpDeg = 192.85948;
private _deNgpDeg = 27.12825;
private _lNcpDeg = 122.93192;

private _dl = _lNcpDeg - _lDeg;
private _sinDec = (sin _deNgpDeg) * (sin _bDeg) + (cos _deNgpDeg) * (cos _bDeg) * (cos _dl);
private _y = (cos _bDeg) * (sin _dl);
private _x = (cos _deNgpDeg) * (sin _bDeg) - (sin _deNgpDeg) * (cos _bDeg) * (cos _dl);

private _raDeg = _raNgpDeg + (_y atan2 _x);
_raDeg = _raDeg mod 360;
if (_raDeg < 0) then { _raDeg = _raDeg + 360; };
private _decDeg = asin _sinDec;

[_raDeg, _decDeg]
