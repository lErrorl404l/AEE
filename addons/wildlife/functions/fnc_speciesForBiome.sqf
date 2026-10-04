#include "..\script_component.hpp"

/*
Biome species selector kernel (wildlife ecology).

Pure: no missionNamespace, no GVAR or EGVAR, no engine command, no random.
It turns the biome, the time of day, the water signal, the vegetation score
and a mission seed into a deterministic array of [class, count] rows.  Two
clients at the same cell and time get the same mix.  The count scales with
the vegetation score, so a zero density and a zero vegetation score return
nothing.

The hashed count uses a small integer hash of the seed and the class index,
so a one-step seed change moves the mix.  The hash stays inside the exactly
representable integer range, so it is identical on every machine.

Arguments:
  0: String - the Koppen biome code
  1: Bool   - night
  2: Number - the water fraction, 0 to 1
  3: Number - the vegetation score, 0 to 1 or higher
  4: Number - the mission seed
  5: Array  - the species table rows [biomeFamily, [class, ...]]

Returns:
  Array - [class, count] rows
*/

params [
    ["_biome", "", [""]],
    ["_isNight", false, [false]],
    ["_waterFrac", 0, [0]],
    ["_vegScore", 0, [0]],
    ["_seed", 0, [0]],
    ["_table", [], [[]]]
];

if (_table isEqualTo []) exitWith { [] };
if (_vegScore <= 0) exitWith { [] };

private _family = "temperate";
private _first = "";
if (_biome isNotEqualTo "") then {
    _first = toLower (_biome select [0, 1]);
};
if (_first == "a") then {
    _family = "tropical";
} else {
    if (_first == "b") then {
        _family = "arid";
    } else {
        if ((_first == "d") || (_first == "e")) then {
            _family = "cold";
        };
    };
};

private _keys = [_family];
if (_waterFrac > 0.5) then {
    _keys pushBack "water";
};

// Collect the classes for every selected overlay, without duplicates.
private _classes = [];
for "_k" from 0 to ((count _keys) - 1) do {
    private _key = _keys select _k;
    for "_t" from 0 to ((count _table) - 1) do {
        private _row = _table select _t;
        if ((_row select 0) == _key) then {
            private _list = _row select 1;
            for "_c" from 0 to ((count _list) - 1) do {
                private _cls = _list select _c;
                private _seen = false;
                for "_s" from 0 to ((count _classes) - 1) do {
                    if ((_classes select _s) == _cls) then { _seen = true; };
                };
                if (!_seen) then { _classes pushBack _cls; };
            };
        };
    };
};

private _span = 1 + (floor ((_vegScore max 0) * 2));
private _out = [];
for "_i" from 0 to ((count _classes) - 1) do {
    private _cls = _classes select _i;
    private _active = true;
    if (_isNight) then {
        if ((_cls == "Hen_random_F") || (_cls == "Cock_random_F") || (_cls == "Cock_white_F")) then {
            _active = false;
        };
    };
    if (_active) then {
        private _hash = ((_seed * 101) + ((_i + 1) * 37)) mod 997;
        if (_hash < 0) then { _hash = -_hash; };
        private _count = 1 + (_hash mod _span);
        _out pushBack [_cls, _count];
    };
};

_out
