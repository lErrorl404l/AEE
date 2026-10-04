#include "..\script_component.hpp"

/*
Cull the live fauna beyond the despawn radius and above the cap.

Client-local.  Dead agents are dropped from the list.  Live agents beyond the
despawn radius are deleted, and any live agent over the hard cap is deleted.
Every removed agent is unregistered from the substrate.  Deletion uses
deleteVehicle; no agent is ever created here.

Arguments:
  0: Array - the listener position

Returns:
  Array - the kept entries [id, agent, class, spawnPosition]
*/

params [["_position", [0, 0, 0], [[]]]];

private _fauna = missionNamespace getVariable [GVAR(fauna), []];
if !(_fauna isEqualType []) then { _fauna = []; };

private _despawn = missionNamespace getVariable [QGVAR(despawnRadius), 600];
if !(_despawn isEqualType 0) then { _despawn = 600; };

private _cap = missionNamespace getVariable [QGVAR(maxAnimals), 16];
if !(_cap isEqualType 0) then { _cap = 16; };

private _anchor = _position;
if ((count _anchor) < 2) then { _anchor = [0, 0, 0]; };

private _kept = [];

for "_i" from 0 to ((count _fauna) - 1) do {
    private _entry = _fauna select _i;
    private _id = _entry select 0;
    private _agent = _entry select 1;
    private _drop = false;

    if (isNull _agent) then {
        _drop = true;
    } else {
        private _distance = (getPos _agent) distance _anchor;
        if (_distance > _despawn) then { _drop = true; };
        if ((!_drop) && ((count _kept) >= _cap)) then { _drop = true; };
    };

    if (_drop) then {
        if (!isNull _agent) then { deleteVehicle _agent; };
        [_id] call EFUNC(ai,agentUnregister);
    } else {
        _kept pushBack _entry;
    };
};

missionNamespace setVariable [GVAR(fauna), _kept];

_kept
