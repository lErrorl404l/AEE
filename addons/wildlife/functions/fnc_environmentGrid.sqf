#include "..\script_component.hpp"

/*
Environment grid cache (wildlife ecology).

Pure: no missionNamespace, no GVAR or EGVAR, no engine command, no random.
It owns the per-cell environment cache: a bounded array of
[cellKey, sample, stamp] rows.  It drops a row older than the environment
horizon, which is the disturbance half-life mirrored from aee_ai, and caps
the store at WILDLIFE_ENVIRONMENT_CAP, keeping the newest rows.  The
neighbourhood sampler writes the store to QGVAR(environment) and reads it
back through this kernel, so one policy owns the bound.

Arguments:
  0: Array  - the store of [cellKey, sample, stamp] rows
  1: Number - the current time, seconds

Returns:
  Array - the bounded, aged store
*/

params [
    ["_store", [], [[]]],
    ["_now", 0, [0]]
];

private _fresh = [];
for "_i" from 0 to ((count _store) - 1) do {
    private _entry = _store select _i;
    if ((_entry isEqualType []) && ((count _entry) >= 3)) then {
        if ((_now - (_entry select 2)) <= WILDLIFE_ENVIRONMENT_HORIZON) then {
            _fresh pushBack _entry;
        };
    };
};

if ((count _fresh) > WILDLIFE_ENVIRONMENT_CAP) then {
    _fresh = _fresh select [((count _fresh) - WILDLIFE_ENVIRONMENT_CAP), WILDLIFE_ENVIRONMENT_CAP];
};

_fresh
