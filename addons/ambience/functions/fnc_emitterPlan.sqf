#include "..\script_component.hpp"

/*
Bounded attached-emitter plan (wildlife ecology, task T27).

Pure: no missionNamespace, no GVAR or EGVAR, no engine command, no random.
For one wildlife tick it decides which fauna keep an attached emitter, which
need one created, and which must be released.  The registry is the list of
already attached emitters [id, key]; the active list is the live animals near
the listener [id, key, distance].  The key is a species/context string, so a
change of key recreates the emitter and an unchanged key leaves it running.

The plan is bounded twice: an animal beyond the radius is never selected, and
only the nearest cap animals are kept.  An emitter is released when its animal
is gone, out of range, over the cap, or its key changed, so a despawn cannot
leak an emitter.  The selection is deterministic: a tie is broken by the
position in the active list, so two machines agree.

Arguments:
  0: Array  - the registry [[id, key], ...]
  1: Array  - the active animals [[id, key, distance], ...]
  2: Number - the emitter cap
  3: Number - the emitter radius, metres

Returns:
  Array - [create, keep, release]; create is [[id, key], ...] and keep and
          release are [id, ...]
*/

params [
    ["_registry", [], [[]]],
    ["_active", [], [[]]],
    ["_cap", WILDLIFE_EMITTER_CAP, [0]],
    ["_radius", WILDLIFE_EMITTER_RADIUS, [0]]
];

private _eligible = [];
for "_i" from 0 to ((count _active) - 1) do {
    private _row = _active select _i;
    if ((_row isEqualType []) && ((count _row) >= 3)) then {
        private _id = _row select 0;
        private _key = _row select 1;
        private _distance = _row select 2;
        if ((_id isEqualType "") && (_key isEqualType "") && (_distance isEqualType 0)) then {
            if ((_distance >= 0) && (_distance <= _radius)) then {
                _eligible pushBack [_id, _key, _distance];
            };
        };
    };
};

// Nearest-first selection, bounded by the cap.  The chosen list holds the
// INDEX of each selected eligible row, so no array set is needed.
private _chosen = [];
private _capN = (_cap max 0);
private _take = (_capN min (count _eligible));
if (_take > 0) then {
    for "_n" from 1 to _take do {
        private _best = -1;
        private _bestDistance = 0;
        for "_i" from 0 to ((count _eligible) - 1) do {
            private _taken = false;
            for "_c" from 0 to ((count _chosen) - 1) do {
                if ((_chosen select _c) == _i) then { _taken = true; };
            };
            if (!_taken) then {
                private _distance = (_eligible select _i) select 2;
                if ((_best < 0) || (_distance < _bestDistance)) then {
                    _best = _i;
                    _bestDistance = _distance;
                };
            };
        };
        if (_best >= 0) then { _chosen pushBack _best; };
    };
};

private _create = [];
private _keep = [];
private _release = [];
private _selectedIds = [];

for "_n" from 0 to ((count _chosen) - 1) do {
    private _row = _eligible select (_chosen select _n);
    private _id = _row select 0;
    private _key = _row select 1;
    _selectedIds pushBack _id;

    private _found = false;
    private _same = false;
    for "_r" from 0 to ((count _registry) - 1) do {
        private _entry = _registry select _r;
        if ((_entry isEqualType []) && ((count _entry) >= 2)) then {
            if ((_entry select 0) == _id) then {
                _found = true;
                if ((_entry select 1) == _key) then { _same = true; };
            };
        };
    };

    if (_same) then {
        _keep pushBack _id;
    } else {
        _create pushBack [_id, _key];
        // A found registry entry with a different key is released, so the
        // wiring deletes the old emitter before it creates the new one.
        if (_found) then { _release pushBack _id; };
    };
};

// Every registry entry whose animal was not selected is released, so a
// despawn, a radius exit and an over-cap emitter all free their source.
for "_r" from 0 to ((count _registry) - 1) do {
    private _entry = _registry select _r;
    if ((_entry isEqualType []) && ((count _entry) >= 2)) then {
        private _id = _entry select 0;
        private _selected = false;
        for "_n" from 0 to ((count _selectedIds) - 1) do {
            if ((_selectedIds select _n) == _id) then { _selected = true; };
        };
        if (!_selected) then {
            private _listed = false;
            for "_rel" from 0 to ((count _release) - 1) do {
                if ((_release select _rel) == _id) then { _listed = true; };
            };
            if (!_listed) then { _release pushBack _id; };
        };
    };
};

[_create, _keep, _release]
