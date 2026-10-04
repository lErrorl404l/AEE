#include "..\script_component.hpp"

/*
Play one local positional one-shot sound.

Client-only.  Refuses when the live instance count is at the cap, and expires
finished instances by time so the count falls again.  The ninth playSound3D
argument is true, so the sound is local and never broadcast.  Every sound is
a vanilla source supplied by the caller.

Arguments:
  0: String - the vanilla sound path
  1: Array  - the position
  2: Number - the volume
  3: Number - the max distance, metres

Returns:
  Bool - true when the sound played
*/

params [
    ["_source", "", [""]],
    ["_position", [0, 0, 0], [[]]],
    ["_volume", 1, [0]],
    ["_distance", WILDLIFE_SOUND_MAX_DISTANCE, [0]]
];

if (!hasInterface) exitWith { false };
if (_source == "") exitWith { false };

private _now = CBA_missionTime;
private _instances = missionNamespace getVariable [QGVAR(soundInstances), []];
if !(_instances isEqualType []) then { _instances = []; };

private _live = [];
for "_i" from 0 to ((count _instances) - 1) do {
    private _expiry = _instances select _i;
    if (_expiry isEqualType 0) then {
        if (_expiry > _now) then {
            _live pushBack _expiry;
        };
    };
};

if ((count _live) >= WILDLIFE_SOUND_INSTANCE_CAP) exitWith { false };

_live pushBack (_now + 3);
missionNamespace setVariable [QGVAR(soundInstances), _live];

playSound3D [_source, objNull, false, ATLToASL _position, _volume, 1, _distance, 0, true];

true
