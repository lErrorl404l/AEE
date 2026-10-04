#include "..\script_component.hpp"

/*
Disturbance sample kernel (reusable AI substrate).

Pure except for the one FUNC call to fnc_stimulusDecay.  Reads the decayed
magnitude at a cell key, or 0 when the cell is not in the field.

Arguments:
  0: Array - the field, an array of [key, magnitude, time] entries
  1: Array - the cell key from fnc_disturbanceKey
  2: Number - the current time, seconds
  3: Number - half-life, seconds

Returns:
  Number - the decayed magnitude at the cell, 0 to 1
*/

params [
    ["_cells", [], [[]]],
    ["_key", [0, 0], [[]]],
    ["_now", 0, [0]],
    ["_halfLife", 45, [0]]
];

private _count = count _cells;
private _result = 0;

for "_i" from 0 to (_count - 1) do {
    private _entry = _cells select _i;
    if (((_entry select 0) select 0) == (_key select 0) && ((_entry select 0) select 1) == (_key select 1)) then {
        _result = [_entry select 1, _now - (_entry select 2), _halfLife] call FUNC(stimulusDecay);
    };
};

_result
