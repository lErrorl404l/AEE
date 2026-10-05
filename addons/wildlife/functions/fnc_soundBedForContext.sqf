#include "..\script_component.hpp"

/*
Ambient sound-bed selector kernel (wildlife ecology).

Pure: no missionNamespace, no GVAR or EGVAR, no engine command, no sound
path.  Picks the context key from the world facts and returns a gain for it.
Water wins, then night, then the biome family.  The gain is the base gain of
the matching manifest row, scaled down by the disturbance and up by the wind
and the rain.

The context key is one of: water, night, day_tropical, day_arid,
day_temperate or day_cold.

Arguments:
  0: String - the Koppen biome code
  1: Bool   - night
  2: Number - the near-water signal, 0 to 1
  3: Number - the wind, metres per second
  4: Number - the disturbance at the listener, 0 to 1
  5: Array  - the manifest rows [contextKey, source, maxDistance, baseGain]
  6: Number - the rain, 0 to 1

Returns:
  Array - [contextKey, gain]
*/

params [
    ["_biome", "", [""]],
    ["_isNight", false, [false]],
    ["_nearWater", 0, [0]],
    ["_wind", 0, [0]],
    ["_disturbance", 0, [0]],
    ["_manifest", [], [[]]],
    ["_rain", 0, [0]]
];

private _key = "day_temperate";
if (_nearWater > 0.5) then {
    _key = "water";
} else {
    if (_isNight) then {
        _key = "night";
    } else {
        private _family = "";
        if (_biome isNotEqualTo "") then {
            _family = toLower (_biome select [0, 1]);
        };
        if (_family == "a") then {
            _key = "day_tropical";
        } else {
            if (_family == "b") then {
                _key = "day_arid";
            } else {
                if ((_family == "d") || (_family == "e")) then {
                    _key = "day_cold";
                };
            };
        };
    };
};

private _base = 0;
for "_i" from 0 to ((count _manifest) - 1) do {
    private _row = _manifest select _i;
    if ((_row select 0) == _key) then {
        if (_base <= 0) then {
            _base = _row select 3;
        };
    };
};

private _dist = ((_disturbance max 0) min 1);
private _windFactor = 1 + (((_wind max 0) min 2) * 0.25);
private _rainFactor = 1 + (((_rain max 0) min 1) * 0.5);
private _gain = _base * (1 - _dist) * _windFactor * _rainFactor;

[_key, ((_gain max 0) min 1)]
