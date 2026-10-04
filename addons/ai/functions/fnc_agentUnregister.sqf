#include "..\script_component.hpp"

/*
Unregister an agent from the reusable substrate.

Arguments:
  0: String - the agent id to remove

Returns:
  Nothing.
*/

params [["_id", "", [""]]];

private _agents = missionNamespace getVariable [QGVAR(agents), []];
private _kept = [];

for "_i" from 0 to ((count _agents) - 1) do {
    private _entry = _agents select _i;
    if (((_entry select 0) != _id)) then {
        _kept pushBack _entry;
    };
};

missionNamespace setVariable [QGVAR(agents), _kept];
