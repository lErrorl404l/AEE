#include "..\..\script_component.hpp"
/*
Peak overpressure level of an explosion (acoustic propagation).  Pure.

Kinney & Graham (1985), "Explosive Shocks in Air", 2nd ed., the side-on
peak overpressure of a TNT charge W at distance R (Z = R / W^1/3, m/kg^1/3):
  dP / p0 = 808 (1 + (Z/4.5)^2)
            / sqrt((1 + (Z/0.048)^2)(1 + (Z/0.32)^2)(1 + (Z/1.35)^2))
The level is 20 log10(dP / 20 uPa) dB peak.

Arguments:
  0: Number - TNT-equivalent charge, kg
  1: Number - distance, m
  2: Number - ambient pressure, Pa (default 101325)
Returns:
  Number - peak level, dB re 20 uPa
*/
params [["_w", 1, [0]], ["_r", 100, [0]], ["_p0", 101325, [0]]];
private _z = (_r max 0.01) / ((_w max 1e-6) ^ (1 / 3));
private _ratio = 808 * (1 + ((_z / 4.5) ^ 2)) / (sqrt ((1 + ((_z / 0.048) ^ 2)) * (1 + ((_z / 0.32) ^ 2)) * (1 + ((_z / 1.35) ^ 2))));
20 * (log ((_ratio * _p0) / 2e-5))
