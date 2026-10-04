#include "..\script_component.hpp"

/*
Register an agent with the reusable substrate.

The registry is one missionNamespace array of entries
[id, anchor, senses, thresholds, actionCallback, recoveryUntil].  Registering
an id that already exists replaces its entry, so a re-register is idempotent.

Arguments:
  0: String - the unique agent id
  1: Object or Array - the anchor, an agent object or a position
  2: Array  - the senses, index 0 is the sense range in metres
  3: Array  - thresholds [flee, freeze, drink, forage]
  4: Code   - the action callback, called [anchor, action, state]
  5: Number - the recovery seconds applied after an action

Returns:
  Nothing.
*/

params [
    ["_id", "", [""]],
    ["_anchor", objNull, [objNull, []]],
    ["_senses", [100], [[]]],
    ["_thresholds", [0.7, 0.3, 0.6, 0.2], [[]]],
    ["_callback", {}, [{}]],
    ["_recovery", 2, [0]]
];

private _agents = missionNamespace getVariable [QGVAR(agents), []];
private _entry = [_id, _anchor, _senses, _thresholds, _callback, 0];
private _found = false;

for "_i" from 0 to ((count _agents) - 1) do {
    if (((_agents select _i) select 0) == _id) then {
        _agents set [_i, _entry];
        _found = true;
    };
};

if (!_found) then {
    _agents pushBack _entry;
};

missionNamespace setVariable [QGVAR(agents), _agents];
