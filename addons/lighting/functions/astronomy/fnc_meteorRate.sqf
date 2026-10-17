#include "..\..\script_component.hpp"

/*
Expected meteor rate for one shower.

Source: International Meteor Organization; Rendtel, J., Arlt, R. and
McBeath, A. (eds.), Handbook for Visual Meteor Observations (IMO, 1st ed.
1995, 2nd ed. 1999).  The rate a single observer sees is the ZHR reduced by
the radiant altitude, the limiting magnitude and the sky obscuration:

    ZHR = N * F * r^(6.5 - lm) / sin(h)

rearranged for the expected rate:

    N = ZHR * sin(h) * r^(limitingMag - 6.5) / F

where h is the radiant altitude, r the shower's population index, and F the
sky-obscuration correction.  F is 1 here: the caller has already gated the
sky on the cloud and the night.  The exponent on sin(h) is 1, the published
form.  The held IMO calendar (IMO INFO 3.1-24) prints the ZHR and r but not
the reduction, so the reduction is cited to the Handbook.

Locked by tools/tests/test_meteors.py.

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
