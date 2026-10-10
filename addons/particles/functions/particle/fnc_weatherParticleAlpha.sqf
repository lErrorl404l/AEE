#include "..\..\script_component.hpp"

/*
Weather-coupled particle alpha (aee-workshop-copy item 7, part 1).

Re-derived from Better Visuals (Workshop 3351805137)
fn_blastWaveEffectMedium.sqf, where the alpha multiplier is
overcast + humidity.  The mod publishes no licence, so this is a re-derived
numeric kernel, not copied code.  No mod content is copied.

The source reads a global humidity that is not an engine command.  The
caller maps it to QEGVAR(core,currentHumidity) / 100, so this kernel takes
humidity as a percent and divides by 100 itself.

The kernel is pure: no missionNamespace, no GVAR or EGVAR, no engine command.
The caller reads overcast and humidity and passes the numbers.

Arguments:
  0: Number - base alpha
  1: Number - overcast 0..1
  2: Number - relative humidity in percent
  3: Number - extra scale

Returns:
  Number - alpha * (overcast + humidityPercent / 100) * scale, clamped 0..2
*/

params [
    ["_alpha", 1, [0]],
    ["_overcast", 0, [0]],
    ["_humidityPercent", 50, [0]],
    ["_scale", 1, [0]]
];

private _value = _alpha * (_overcast + (_humidityPercent / 100)) * _scale;
(_value max 0) min 2
