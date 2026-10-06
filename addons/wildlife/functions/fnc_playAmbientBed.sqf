#include "..\script_component.hpp"

/*
Play the ambient bed for one context.

Client-only.  A raw vanilla file is replayed through the local one-shot path,
which carries the gain.  A vanilla CfgSFX class becomes one local looping
positional source, and the previous source is deleted first so the bed does
not stack.

The looping source is recreated ONLY when the source key changes, not on every
tick.  A recreate each tick restarted the CfgSFX and defeated its own random
repeat delay (0 to 30 s for the owl and bird banks).  The key is the CfgSFX
class string.

Limit: the client-local sound-source command takes no gain, so a CfgSFX bed
cannot be attenuated in place.  A caller that needs the silence model on the
source uses the scheduled one-shot path (fnc_soundTick and fnc_playOneShot)
instead.

Arguments:
  0: String - the vanilla sound path or CfgSFX class
  1: Array  - the position
  2: Number - the gain (used by the one-shot path only)

Returns:
  Nothing.
*/

params [
    ["_source", "", [""]],
    ["_position", [0, 0, 0], [[]]],
    ["_gain", 1, [0]]
];

if (!hasInterface) exitWith {};
if (_source == "") exitWith {};

if ((_source find ".") >= 0) then {
    [_source, _position, _gain, WILDLIFE_SOUND_MAX_DISTANCE] call FUNC(playOneShot);
} else {
    // Recreate the looping source only on a key change.  The same key with a
    // live source leaves the bed running, so the class carries its own repeat.
    private _key = missionNamespace getVariable [QGVAR(ambientKey), ""];
    if !(_key isEqualType "") then { _key = ""; };
    private _current = missionNamespace getVariable [QGVAR(ambientSource), objNull];
    if ((_key == _source) && (!isNull _current)) exitWith {};
    // The previous local source is deleted before the new one is created, so
    // the bed holds at most one instance.
    if (!isNull _current) then {
        deleteVehicle _current;
    };
    private _sourceObject = createSoundSourceLocal [_source, _position, [], 0];
    missionNamespace setVariable [QGVAR(ambientSource), _sourceObject];
    missionNamespace setVariable [QGVAR(ambientKey), _source];
};
