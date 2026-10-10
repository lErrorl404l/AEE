#include "..\..\script_component.hpp"

/*
Cold stress kernel (will to live).

Pure: no missionNamespace, no GVAR or EGVAR, no engine command.  Maps the
wind chill temperature to the cold-stress risk the survival model consumes.

The wind chill comes from the Environment Canada / NWS index (computed by
strain/calculateColdWeatherPerformance).  The TB MED 508 frostbite bands:

  low        0 to -9 C     no risk
  moderate   -10 to -27 C  long exposure
  high       -28 to -39 C  10-30 min
  very high  -40 to -47 C  5-10 min
  severe     -48 to -54 C  2-5 min
  extreme    -55 C or less under 2 min

The survival calibration anchors the risk at -28 C = 0.3, -40 = 0.6,
-48 = 0.8 and -55 = 1.0, and the risk is linear between the anchors.  The
onset anchor at -10 C is the top of the TB MED 508 low band.

Arguments:
  0: Number - wind chill temperature, degC

Returns:
  Number - the cold stress risk, 0 to 1
*/

params [["_windChill", 0, [0]]];

private _risk = 0;
if (_windChill <= -55) then {
    _risk = 1;
} else {
    if (_windChill <= -48) then {
        _risk = 0.8 + (-48 - _windChill) * (0.2 / 7);
    } else {
        if (_windChill <= -40) then {
            _risk = 0.6 + (-40 - _windChill) * (0.2 / 8);
        } else {
            if (_windChill <= -28) then {
                _risk = 0.3 + (-28 - _windChill) * (0.3 / 12);
            } else {
                if (_windChill < -10) then {
                    _risk = (-10 - _windChill) * (0.3 / 18);
                };
            };
        };
    };
};

((_risk max 0) min 1)
