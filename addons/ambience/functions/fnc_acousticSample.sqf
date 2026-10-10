#include "..\script_component.hpp"

/*
Acoustic event bus sample kernel (wildlife ecology).

Pure: no missionNamespace, no GVAR or EGVAR, no engine command, no random.
It reads the bounded bus at one listener, keeps the events inside the
horizon, and returns the strongest propagated level and its kind.  The level
is the auditory stimulus for the listener, so a gunshot and a footstep are
ordered by their propagated level, not by a fixed range.

It calls fnc_acousticLevel, so the spreading, the weather absorption and the
occlusion live in one kernel.

Arguments:
  0: Array  - the bus, an array of [pos, sourceDb, kind, stamp] rows
  1: Array  - the listener position, ASL
  2: Number - the current time, seconds
  3: Number - the event horizon, seconds
  4: Number - the propagation index, 0.3 to 2.0
  5: Array  - occluder positions, ASL

Returns:
  Array - [level, kind], the strongest stimulus 0 to 1 and its kind
*/

params [
    ["_events", [], [[]]],
    ["_listenerPos", [0, 0, 0], [[]]],
    ["_now", 0, [0]],
    ["_horizon", WILDLIFE_ACOUSTIC_EVENT_HORIZON, [0]],
    ["_propagationIndex", 1, [0]],
    ["_occluders", [], [[]]]
];

private _live = [];
for "_i" from 0 to ((count _events) - 1) do {
    private _entry = _events select _i;
    if ((_entry isEqualType []) && ((count _entry) >= 4)) then {
        if ((_now - (_entry select 3)) <= _horizon) then {
            _live pushBack [_entry select 0, _entry select 1, _entry select 2];
        };
    };
};

private _levels = [
    _live, _listenerPos, _propagationIndex, _occluders,
    WILDLIFE_ACOUSTIC_OCCLUSION_DB, WILDLIFE_ACOUSTIC_OCCLUSION_RADIUS_M,
    WILDLIFE_ACOUSTIC_HEARING_FLOOR_DB, WILDLIFE_ACOUSTIC_LOUD_DB
] call FUNC(acousticLevel);

private _level = 0;
private _kind = "";
for "_i" from 0 to ((count _levels) - 1) do {
    private _row = _levels select _i;
    if ((_row select 1) > _level) then {
        _level = _row select 1;
        _kind = _row select 0;
    };
};

[_level, _kind]
