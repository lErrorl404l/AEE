#include "..\..\script_component.hpp"

/*
Weather-coupled heat-haze alpha (aee-workshop-copy item 7, part 1).

Re-derived from Better Visuals (Workshop 3351805137) fn_heatHaze.sqf, where
the haze alpha is (ambientTemperature # 0) / 100 clamped to 0.15..0.45.  The
mod publishes no licence, so this is a re-derived numeric kernel, not copied
code.  No mod content is copied.

ambientTemperature is an engine array, not a number.  The caller takes
element 0 and passes the number, so this kernel stays pure.  The source
clamps with two if statements.  The bounds are parameters here, so the caller
can raise the ceiling with a setting.

The kernel is pure: no missionNamespace, no GVAR or EGVAR, no engine command.

Arguments:
  0: Number - ambient air temperature in Celsius (ambientTemperature # 0)
  1: Number - lower clamp
  2: Number - upper clamp

Returns:
  Number - ambientTemperature / 100 clamped to min..max
*/

params [
    ["_ambientTemperature", 20, [0]],
    ["_min", 0.15, [0]],
    ["_max", 0.45, [0]]
];

private _value = _ambientTemperature / 100;
(_value max _min) min _max
