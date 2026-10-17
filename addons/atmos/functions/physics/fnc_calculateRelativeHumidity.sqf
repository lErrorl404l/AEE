#include "..\..\script_component.hpp"
/*
Relative humidity at the current temperature from the day's vapour content.

The water-vapour pressure of the near-surface air changes far less over a
day than the temperature, so it is held at the day's value
  e = RH_mean / 100 * e_w(T_mean)
and the relative humidity follows the temperature:
  RH = 100 * e / e_w(T_now),   capped at saturation.
e_w is the saturation vapour pressure over water (WMO-No. 8, Annex 4.B,
Magnus form): e_w(t) = 6.112 exp(17.62 t / (243.12 + t)) hPa.  A warm
afternoon dries the air, a cool night moistens it, and air that cools to
its dew point saturates (the fog model takes the excess as liquid water).

Pure: no missionNamespace, no GVAR or EGVAR, no engine command.

Arguments:
  0: Number - the day's mean relative humidity (climate normal), %
  1: Number - the day's mean temperature, degrees Celsius
  2: Number - current temperature, degrees Celsius
Returns:
  Number - relative humidity, % (integer, 0 to 100)
*/
params [
    ["_rhMean", 50, [0]],
    ["_tMean", 15, [0]],
    ["_tNow", 15, [0]]
];
private _magnusA = 6.112;
private _magnusB = 17.62;
private _magnusC = 243.12;
private _saturation = 100;
private _e = ((_rhMean max 0) min _saturation) / 100 * _magnusA * exp (_magnusB * _tMean / (_magnusC + _tMean));
private _ew = _magnusA * exp (_magnusB * _tNow / (_magnusC + _tNow));
round (((100 * _e / _ew) max 0) min _saturation)
