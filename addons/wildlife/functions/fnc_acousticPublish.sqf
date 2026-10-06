#include "..\script_component.hpp"

/*
Acoustic event bus publish kernel (wildlife ecology).

Pure: no missionNamespace, no GVAR or EGVAR, no engine command, no random.
It appends one sound event to the bounded local bus and drops the entries
older than the horizon.  Sound is an instantaneous event, so an entry ages
out after the horizon instead of decaying in place.  The bus is capped,
keeping the newest entries, so a burst of fire cannot grow it without bound.

The bus row is [sourcePos ASL, sourceLevelDb, kind, stamp].  The owner writes
it to QGVAR(soundEvents) and reads it back through fnc_acousticSample.

Arguments:
  0: Array  - the bus, an array of [pos, sourceDb, kind, stamp] rows
  1: Array  - the source position, ASL
  2: Number - the source level, dB
  3: String - the event kind
  4: Number - the current time, seconds
  5: Number - the bus cap
  6: Number - the event horizon, seconds

Returns:
  Array - the bounded, aged bus
*/

params [
    ["_events", [], [[]]],
    ["_pos", [0, 0, 0], [[]]],
    ["_sourceDb", 0, [0]],
    ["_kind", "", [""]],
    ["_now", 0, [0]],
    ["_cap", WILDLIFE_ACOUSTIC_EVENT_CAP, [0]],
    ["_horizon", WILDLIFE_ACOUSTIC_EVENT_HORIZON, [0]]
];

private _fresh = [];
for "_i" from 0 to ((count _events) - 1) do {
    private _entry = _events select _i;
    if ((_entry isEqualType []) && ((count _entry) >= 4)) then {
        if ((_now - (_entry select 3)) <= _horizon) then {
            _fresh pushBack _entry;
        };
    };
};

_fresh pushBack [_pos, _sourceDb, _kind, _now];

if ((count _fresh) > _cap) then {
    _fresh = _fresh select [((count _fresh) - _cap), _cap];
};

_fresh
