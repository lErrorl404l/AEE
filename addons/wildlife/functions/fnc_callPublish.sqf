#include "..\script_component.hpp"

/*
Call publish kernel (wildlife ecology).

Pure: no missionNamespace, no GVAR or EGVAR, no engine command, no random.
It appends a heard-call row to the bus, then drops every expired row and caps
the store, keeping the newest.  The bus mirrors the disturbance field: the
same cell key, the same horizon and the same cap.  A row is
[cellKey, callType, urgency, species, expiry], where expiry is the absolute
mission time the row stops being heard.

The cap and the horizon arrive from the caller's policy, so no policy lives
here.  Deterministic, so two machines with the same bus and time agree.

Arguments:
  0: Array  - the bus
  1: Array  - the cell key from fnc_disturbanceKey
  2: String - the call type
  3: Number - the urgency, 0 to 1
  4: String - the species that called
  5: Number - the current time, seconds

Returns:
  Array - the new bus
*/

params [
    ["_bus", [], [[]]],
    ["_key", [0, 0], [[]]],
    ["_callType", "", [""]],
    ["_urgency", 0, [0]],
    ["_species", "", [""]],
    ["_now", 0, [0]]
];

if (_callType == "") exitWith { _bus };

private _out = [];
for "_i" from 0 to ((count _bus) - 1) do {
    _out pushBack (_bus select _i);
};
_out pushBack [_key, _callType, ((_urgency max 0) min 1), _species, _now + WILDLIFE_CALL_HORIZON];

private _fresh = [];
for "_i" from 0 to ((count _out) - 1) do {
    private _row = _out select _i;
    if ((_row isEqualType []) && ((count _row) >= 5)) then {
        if ((_row select 4) >= _now) then { _fresh pushBack _row; };
    };
};

if ((count _fresh) > WILDLIFE_CALL_BUDGET) then {
    _fresh = _fresh select [((count _fresh) - WILDLIFE_CALL_BUDGET), WILDLIFE_CALL_BUDGET];
};

_fresh
