#include "..\script_component.hpp"

/*
Biome species selector (DEPRECATED).

Deprecated: use aee_wildlife_fnc_getSpeciesMatch, which reads the true sun
elevation, the air temperature and the month.  This shim keeps the old
signature and the old [class, count] output for the callers that still use
it.  It describes the legacy table as one group per family and forwards the
family, overlay, season, temperature and activity decision to the matcher,
then maps the surviving families back to the legacy classes.  The single INFO
deprecation is emitted by fnc_speciesDeprecation.

Pure: no engine command and no random.  The fixed temperature and month stand
in for inputs the legacy callers never passed.

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

[] call FUNC(speciesDeprecation);

// Describe the legacy table as one open group per family, so the matcher owns
// the family, overlay, season, temperature and activity decision.
private _corpus = [];
for "_t" from 0 to ((count _table) - 1) do {
    private _family = (_table select _t) select 0;
    _corpus pushBack [
        _family, _family, [], "diurnal",
        [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12], [-60, 60],
        [100, 0], [1, 0, false], "mixed",
        [0, 0, 0, 0], [1, 1, 1, 1, 1, 1, 1], false, "none", "R"
    ];
};

private _sunElevationDeg = 30;
if (_isNight) then { _sunElevationDeg = -20; };

private _matches = [
    _biome, _sunElevationDeg, 18, 6, _waterFrac, _vegScore,
    "ground", 0, [0, 0, 0], _seed, _corpus
] call FUNC(getSpeciesMatch);

private _span = 1 + (floor ((_vegScore max 0) * 2));
private _out = [];
for "_m" from 0 to ((count _matches) - 1) do {
    private _family = (_matches select _m) select 0;
    for "_t" from 0 to ((count _table) - 1) do {
        if (((_table select _t) select 0) == _family) then {
            private _classes = (_table select _t) select 1;
            for "_c" from 0 to ((count _classes) - 1) do {
                private _class = _classes select _c;
                private _hash = ((_seed * 101) + ((_c + 1) * 37) + ((_t + 1) * 53)) mod 997;
                if (_hash < 0) then { _hash = -_hash; };
                _out pushBack [_class, 1 + (_hash mod _span)];
            };
        };
    };
};

_out
