#include "..\script_component.hpp"

/*
AI hearing range kernel.

Applies AEE's single sound-propagation model to a baseline hearing range.  The
propagation index is aee_weather_currentSoundPropagation (0.3 to 2.0, 1.0 =
baseline), computed once per environment tick by
addons/weather/functions/terrain/fnc_updateSoundPropagation.sqf from the
temperature inversion, the wind, the rain, the foliage and the snow.  This
kernel adds no second propagation model: it scales the range by that index
alone, so an index above 1 carries the shot further and below 1 shorter.

Pure: no missionNamespace, no GVAR or EGVAR, no engine command.

Arguments:
  0: Number - the baseline hearing range, metres
  1: Number - the propagation index, 0.3 to 2.0

Returns:
  Number - the effective hearing range, metres
*/

params [
    ["_baseRange", 0, [0]],
    ["_index", 1, [0]]
];

(_baseRange max 0) * ((_index max 0.3) min 2.0)
