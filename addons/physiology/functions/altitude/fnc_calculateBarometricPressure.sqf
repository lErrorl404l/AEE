#include "..\..\script_component.hpp"
/*
ICAO standard atmosphere barometric pressure (issue #135).

P = P0 * (1 - L*h/T0)^(g/(R*L))  for the troposphere (0-11,000 m),
then isothermal exponential decay above (stratosphere, T = 216.65 K).

Constants (ICAO Doc 7488 / ISO 2533 / US Standard Atmosphere 1976):
  P0 = 101325 Pa, T0 = 288.15 K, L = 0.0065 K/m, g = 9.80665 m/s^2,
  R = 287.05287 J/(kg*K) (specific gas constant), exponent 5.25588.
  Tropopause: 11,000 m, P = 22632.1 Pa, T = 216.65 K.

Verified pressure anchors:
  0.5 bar  ~ 5,500 m  (18,000 ft)   - troposphere
  0.25 bar ~ 10,300 m (34,000 ft)   - troposphere (near tropopause)
  0.1 bar  ~ 16,200 m (53,000 ft)   - stratosphere (needs the
                                      isothermal layer, NOT the
                                      tropospheric formula)

Input:  [_altM] - geometric altitude in metres (getPosASL)
Output: ambient pressure in bar (1.01325 at sea level)
*/
params [["_altM", 0, [0]]];

private _alt = _altM max 0;

private _pBar = if (_alt <= 11000) then {
    // Troposphere: standard power law
    (101325 * ((1 - (0.0065 * _alt / 288.15)) ^ 5.25588)) / 100000
} else {
    // Stratosphere: isothermal exponential decay from the tropopause
    (22632.1 * exp (-9.80665 * (_alt - 11000) / (287.05287 * 216.65))) / 100000
};

_pBar
