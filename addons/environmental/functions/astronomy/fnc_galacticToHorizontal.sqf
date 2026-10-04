#include "..\..\script_component.hpp"

/*
Galactic coordinates to horizontal coordinates.

Composes FUNC(galacticToEquatorial) with the same hour-angle and alt/az
formulas fnc_getStarCatalog inlines (Meeus, Astronomical Algorithms, Ch. 13;
azimuth from north clockwise).  The Milky Way sampler calls this once per band
sample, so the band follows the sidereal motion with the starfield.

The kernel is pure.  The caller passes the local sidereal time (_lstDeg) and
the observer latitude (_latDeg); the function does not call FUNC(siderealTime)
and does not read missionNamespace.  In tests, FUNC(galacticToEquatorial) is
injected through globals_ (tools/tests/sqf_lite.py::run_sqf).

Arguments:
  0: Number - galactic longitude, degrees
  1: Number - galactic latitude, degrees
  2: Number - local sidereal time, degrees
  3: Number - observer latitude, degrees

Returns:
  Array [altDeg, azDeg] - altitude above the horizon and azimuth from north,
  clockwise, azimuth normalised to [0, 360).
*/

params [
    ["_lDeg", 0, [0]],
    ["_bDeg", 0, [0]],
    ["_lstDeg", 0, [0]],
    ["_latDeg", 45, [0]]
];

private _equatorial = [_lDeg, _bDeg] call FUNC(galacticToEquatorial);
private _raDeg = _equatorial select 0;
private _decDeg = _equatorial select 1;

// Hour angle (degrees), normalised to [-180, 180].
private _haDeg = _lstDeg - _raDeg;
if (_haDeg > 180) then { _haDeg = _haDeg - 360; };
if (_haDeg < -180) then { _haDeg = _haDeg + 360; };

// Altitude above the horizon (degrees).
private _altDeg = asin (sin _decDeg * sin _latDeg
    + cos _decDeg * cos _latDeg * cos _haDeg);

// Azimuth from north, clockwise.  The Meeus Ch. 13 atan2 form measures from
// the south, westward; add 180 degrees for the north convention
// fnc_starDirection documents and consumes.
private _azDeg = ((sin _haDeg) atan2 (cos _haDeg * sin _latDeg - tan _decDeg * cos _latDeg)) + 180;
_azDeg = _azDeg mod 360;
if (_azDeg < 0) then { _azDeg = _azDeg + 360; };

[_altDeg, _azDeg]
