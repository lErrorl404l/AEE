#include "..\..\script_component.hpp"

/*
Radiant equatorial coordinates to horizontal coordinates.

Given a meteor shower radiant (right ascension and declination) and the
observer's latitude and local sidereal time, return the radiant altitude
and azimuth by the same spherical trigonometry fnc_getStarCatalog applies
to stars.  The hour angle is normalised to [-180, 180]; the azimuth is
normalised to [0, 360).

No precession: IMO radiants are current-epoch and the J2000 correction is
below the precision the calendar publishes.

Arguments:
  0: Number - right ascension, degrees
  1: Number - declination, degrees
  2: Number - observer latitude, degrees
  3: Number - local sidereal time, degrees
Returns:
  Array [altDeg, azDeg] - altitude above the horizon and azimuth from north,
  clockwise, both in degrees.
*/

params [
    ["_raDeg", 0, [0]],
    ["_decDeg", 0, [0]],
    ["_latDeg", 0, [0]],
    ["_lstDeg", 0, [0]]
];

// Hour angle (degrees), normalised to [-180, 180].
private _haDeg = _lstDeg - _raDeg;
if (_haDeg > 180) then { _haDeg = _haDeg - 360; };
if (_haDeg < -180) then { _haDeg = _haDeg + 360; };

// Altitude above the horizon (degrees).
private _altDeg = asin (sin _decDeg * sin _latDeg
    + cos _decDeg * cos _latDeg * cos _haDeg);

// Azimuth (degrees from north, clockwise).  The Meeus Ch. 13 atan2 form
// measures from the south, westward; add 180 degrees to reach the north
// convention fnc_starDirection documents and consumes.
private _azDeg = ((sin _haDeg) atan2 (cos _haDeg * sin _latDeg - tan _decDeg * cos _latDeg)) + 180;
_azDeg = _azDeg mod 360;
if (_azDeg < 0) then { _azDeg = _azDeg + 360; };

[_altDeg, _azDeg]
