#include "..\script_component.hpp"

/*
Receive a broadcast stimulus and apply it to the local field.

Called by remoteExecCall from fnc_reportStimulus.  The apply is idempotent, so
a receiver that already holds the cell keeps the stronger magnitude.  The
dedicated server holds no field, so it exits.

Arguments:
  0: Array - the payload [position, magnitude, time]

Returns:
  Nothing.
*/

params [["_payload", [], [[]]]];
_payload params [
    ["_pos", [0, 0, 0], [[]]],
    ["_magnitude", 0, [0]],
    ["_time", 0, [0]]
];

if (isDedicated) exitWith {};

private _key = [_pos] call FUNC(disturbanceKey);
private _field = missionNamespace getVariable [QGVAR(disturbance), []];
_field = [_field, _key, _magnitude, _time] call FUNC(disturbanceApply);
missionNamespace setVariable [QGVAR(disturbance), _field];
