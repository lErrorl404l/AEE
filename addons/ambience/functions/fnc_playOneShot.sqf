#include "..\script_component.hpp"

/*
Play one local one-shot sound, optionally attached to a moving object.

Client-only.  Refuses when the live instance count is at the cap, and expires
finished instances by time so the count falls again.  The ninth playSound3D
argument is true, so the sound is local and never broadcast.  Every sound is
a vanilla source supplied by the caller.

The optional fifth argument is the emitter object.  When it is a live object,
playSound3D takes it as the sound source, so the sound tracks the object as it
moves.  This is generic: the emitter is whatever fauna object the caller
passes, so a custom animal needs no extra code.  An empty (null) emitter keeps
the positional behaviour for the ambient layer.  The sixth argument is the
pitch; the caller derives it from fnc_callPitch, so no call carries a fixed
pitch.

Arguments:
  0: String - the vanilla sound path
  1: Array  - the position, used when no emitter object is given
  2: Number - the volume
  3: Number - the max distance, metres
  4: Object - the emitter object, objNull for a fixed position
  5: Number - the pitch multiplier

Returns:
  Bool - true when the sound played
*/

params [
    ["_source", "", [""]],
    ["_position", [0, 0, 0], [[]]],
    ["_volume", 1, [0]],
    ["_distance", WILDLIFE_SOUND_MAX_DISTANCE, [0]],
    ["_attachTo", objNull, [objNull]],
    ["_pitch", 1, [0]]
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

// An emitter object makes the engine take the sound from that object, so the
// call tracks the animal.  A null emitter keeps the positional form.  The
// pitch carries the seeded jitter and the Doppler shift from fnc_callPitch.
if (isNull _attachTo) then {
    playSound3D [_source, objNull, false, ATLToASL _position, _volume, _pitch, _distance, 0, true];
} else {
    playSound3D [_source, _attachTo, false, getPosASL _attachTo, _volume, _pitch, _distance, 0, true];
};

true
