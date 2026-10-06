#include "..\script_component.hpp"

/*
Deterministic weighted bed-source pick (wildlife ecology).

Pure: no missionNamespace, no GVAR or EGVAR, no engine command, no random.
It replaces the first-match scan that collapsed every multi-row context to a
single file.  Every manifest row whose key matches is a candidate, and a
seeded deterministic draw over the row gains selects one.  The same seed and
the same rows return the same source on any machine, so two clients agree.

A row gain is the row's base gain and is therefore positive, so the walk over
the candidate rows reaches every one of them as the seed advances.  An empty
match returns the empty string, which the caller treats as no bed.

Arguments:
  0: Array  - the manifest rows [contextKey, source, maxDistance, baseGain]
  1: String - the context key
  2: Number - the seed, 0 or more

Returns:
  String - the selected source, or "" when no row matches the key
*/

params [
    ["_manifest", [], [[]]],
    ["_key", "", [""]],
    ["_seed", 0, [0]]
];

private _rows = [];
for "_i" from 0 to ((count _manifest) - 1) do {
    private _row = _manifest select _i;
    if (((_row select 0) == _key) && ((count _row) >= 4)) then { _rows pushBack _row; };
};

if (_rows isEqualTo []) exitWith { "" };

private _total = 0;
for "_i" from 0 to ((count _rows) - 1) do {
    private _gain = (_rows select _i) select 3;
    if (_gain isEqualType 0) then { _total = _total + ((_gain max 0)); };
};

if (_total <= 0) exitWith { (_rows select 0) select 1 };

private _target = (((((_seed mod 1000) max 0) / 1000)) * _total);

private _source = "";
private _acc = 0;
private _picked = false;
for "_i" from 0 to ((count _rows) - 1) do {
    if (!_picked) then {
        private _row = _rows select _i;
        private _gain = (_row select 3) max 0;
        _acc = _acc + _gain;
        if (_target < _acc) then {
            _source = _row select 1;
            _picked = true;
        };
    };
};

if (!_picked) then { _source = (_rows select 0) select 1; };

_source
