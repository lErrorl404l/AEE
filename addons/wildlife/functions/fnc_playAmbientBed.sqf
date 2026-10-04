#include "..\script_component.hpp"

/*
Play the ambient bed for one context.

Client-only.  A raw vanilla file is replayed through the local one-shot path.
A vanilla CfgSFX class becomes one local looping positional source, and the
previous source is deleted first so the bed does not stack.

Arguments:
  0: String - the vanilla sound path or CfgSFX class
  1: Array  - the position
  2: Number - the gain

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
    private _current = missionNamespace getVariable [QGVAR(ambientSource), objNull];
    if (!isNull _current) then {
        deleteVehicle _current;
    };
    private _sourceObject = createSoundSource [_source, _position, [], 0];
    missionNamespace setVariable [QGVAR(ambientSource), _sourceObject];
};
