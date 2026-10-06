#include "..\script_component.hpp"

/*
Call sample kernel (wildlife ecology).

Pure: no missionNamespace, no GVAR or EGVAR, no engine command, no random.
It reads the strongest live call at one cell.  An expired row is never
returned.  A row with no urgency or a malformed shape is ignored.  The
result is [callType, urgency, species], or empty when the cell is silent.
The receiver then decodes it with fnc_callReceive.

Arguments:
  0: Array  - the bus
  1: Array  - the cell key from fnc_disturbanceKey
  2: Number - the current time, seconds

Returns:
  Array - [callType, urgency, species] or []
*/

params [
    ["_bus", [], [[]]],
    ["_key", [0, 0], [[]]],
    ["_now", 0, [0]]
];

private _result = [];
private _best = -1;

for "_i" from 0 to ((count _bus) - 1) do {
    private _row = _bus select _i;
    if ((_row isEqualType []) && ((count _row) >= 5)) then {
        if ((_row select 4) >= _now) then {
            private _rkey = _row select 0;
            if ((_rkey isEqualType []) && ((count _rkey) >= 2)) then {
                if (((_rkey select 0) == (_key select 0)) && ((_rkey select 1) == (_key select 1))) then {
                    private _urgency = _row select 2;
                    if ((_urgency isEqualType 0) && (_urgency > _best)) then {
                        _best = _urgency;
                        _result = [_row select 1, _row select 2, _row select 3];
                    };
                };
            };
        };
    };
};

_result
