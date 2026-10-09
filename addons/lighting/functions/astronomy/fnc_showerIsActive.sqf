#include "..\..\script_component.hpp"

/*
Is a shower active on the given calendar date?

The activity window is inclusive.  When the start key (month * 100 + day)
exceeds the end key the window wraps the year end, as the Quadrantids do
(Dec 28 to Jan 12).

Arguments:
  0: Number - month (1..12)
  1: Number - day (1..31)
  2: Array  - shower row [code, name, startMonth, startDay, endMonth, endDay, ...]
Returns:
  Boolean - true when the date is inside the window.
*/

params [
    ["_month", 1, [0]],
    ["_day", 1, [0]],
    ["_shower", [], [[]]]
];

private _startKey = (_shower select 2) * 100 + (_shower select 3);
private _endKey = (_shower select 4) * 100 + (_shower select 5);
private _key = _month * 100 + _day;

private _active = false;
if (_startKey <= _endKey) then {
    _active = _key >= _startKey && _key <= _endKey;
} else {
    _active = _key >= _startKey || _key <= _endKey;
};

_active
