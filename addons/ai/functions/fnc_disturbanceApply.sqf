#include "..\script_component.hpp"

/*
Disturbance apply kernel (reusable AI substrate).

Pure: no missionNamespace, no GVAR or EGVAR, no engine command.  Raises a
cell to the new stimulus when the new stimulus is stronger, otherwise keeps
the existing entry.  A missing cell is appended.  Cells not in the field are
unchanged.  The cell cap and the age prune are the field owner's job, not
this kernel's.

Arguments:
  0: Array - the field, an array of [key, magnitude, time] entries
  1: Array - the cell key from fnc_disturbanceKey
  2: Number - the new stimulus magnitude, 0 to 1
  3: Number - the current time, seconds

Returns:
  Array - the new field
*/

params [
    ["_cells", [], [[]]],
    ["_key", [0, 0], [[]]],
    ["_magnitude", 0, [0]],
    ["_now", 0, [0]]
];

private _count = count _cells;
private _out = [];
private _found = false;

for "_i" from 0 to (_count - 1) do {
    private _entry = _cells select _i;
    if (((_entry select 0) select 0) == (_key select 0) && ((_entry select 0) select 1) == (_key select 1)) then {
        private _raised = (_entry select 1) max _magnitude;
        _out = _out + [[_key, _raised, _now]];
        _found = true;
    } else {
        _out = _out + [_entry];
    };
};

if (!_found) then {
    _out = _out + [[_key, _magnitude, _now]];
};

_out
