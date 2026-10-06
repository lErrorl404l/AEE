#include "..\script_component.hpp"

/*
Release the attached emitter for one animal (wildlife ecology, task T27).

Client-only wiring.  It deletes the sound source attached to the given fauna
id and drops its registry row, so a culled or despawned animal cannot leak a
looping emitter.  The check is by id, so it is safe to call for an animal that
has no emitter.

Arguments:
  0: String - the fauna id

Returns:
  Number - the number of emitters released (0 or 1)
*/

params [
    ["_id", "", [""]]
];

if (_id == "") exitWith { 0 };

if (!hasInterface) exitWith { 0 };

private _emitters = missionNamespace getVariable [QGVAR(emitters), []];
if !(_emitters isEqualType []) then { _emitters = []; };

private _kept = [];
private _released = 0;
for "_i" from 0 to ((count _emitters) - 1) do {
    private _row = _emitters select _i;
    if ((_row isEqualType []) && ((count _row) >= 3) && ((_row select 0) == _id)) then {
        private _source = _row select 2;
        if (!isNull _source) then { deleteVehicle _source; };
        _released = _released + 1;
    } else {
        _kept pushBack _row;
    };
};

missionNamespace setVariable [QGVAR(emitters), _kept];
_released
