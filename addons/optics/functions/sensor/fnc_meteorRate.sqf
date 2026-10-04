#include "..\..\script_component.hpp"

/*
Expected meteor rate for one shower.

UNSOURCED: the held calendar (IMO INFO 3.1-24) defines the Zenithal Hourly
Rate - an ideal observer under a clear sky at the reference limiting
magnitude +6.5, with the radiant overhead, sees ZHR meteors per hour.  The
calendar does NOT print the reduction applied at a lower radiant altitude or
a different limiting magnitude.  This function implements the standard
relation:

    N = ZHR * sin(alt) * r ^ (limitingMag - 6.5)

where r is the shower's population index.  It is marked UNSOURCED against
the held file and is locked by tools/tests/test_meteors.py.

Arguments:
  0: Number - ZHR, meteors per hour
  1: Number - population index r
  2: Number - radiant altitude, degrees
  3: Number - limiting magnitude
Returns:
  Number - expected meteors per hour, never below zero.
*/

params [
    ["_zhr", 0, [0]],
    ["_r", 1, [0]],
    ["_altDeg", 0, [0]],
    ["_limitingMag", 6.5, [0]]
];

if (_altDeg <= 0) exitWith { 0 };

private _sinAlt = sin _altDeg;
private _rate = _zhr * _sinAlt * (_r ^ (_limitingMag - 6.5));

(_rate max 0)
