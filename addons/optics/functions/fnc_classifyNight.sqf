#include "..\script_component.hpp"

/*
DEF Stan 61-027 night classification from sun elevation and moon
illumination phase.

Twilight boundaries match IAU astronomical twilight standards.  Moon
criteria follow DEF Stan 61-027 military lighting restriction levels.

Classification (integer 0-4):
  0 = Day:              sunElev > -6
  1 = Civil Twilight:   sunElev -6 to -12
  2 = Nautical Twilight: sunElev -12 to -18
  3 = Full Night:        sunElev < -18, moonPhase >= 10%
  4 = Dark Night:        sunElev < -18, moonPhase < 10%

DEF Stan 61-027 defines lighting restrictions by twilight zone:
  RESTRICTED: civil twilight (sun -6 to -12 deg)
  HEAVY RESTRICTION: nautical twilight (sun -12 to -18 deg)
  BLACKOUT: astronomical night (sun < -18 deg)
Dark night (sun < -18, moon phase < 10%) is the mildest blackout tier
where no meaningful moonlight reaches the ground.

Stores: QGVAR(nightClassification) as integer 0-4.
Returns: night classification integer.
*/

params [
    ["_sunElev", -90, [0]],
    ["_moonPhase", 0, [0]]
];

private _classification = 0;

if (_sunElev > -6) then {
    _classification = 0;
} else {
    if (_sunElev > -12) then {
        _classification = 1;
    } else {
        if (_sunElev > -18) then {
            _classification = 2;
        } else {
            // Astronomical night: classify by moon illumination.
            // DEF Stan 61-027: dark night when moon contributes
            // negligible illumination (< 10% phase).
            if (_moonPhase < 0.10) then {
                _classification = 4;
            } else {
                _classification = 3;
            };
        };
    };
};

missionNamespace setVariable [QGVAR(nightClassification), _classification];

_classification
