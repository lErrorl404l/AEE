#include "..\script_component.hpp"

/*
Reveal a sound source to the AI that can hear it.

The engine hearing cannot be scaled directly: audibleFire is a config property,
not a command.  The engine's knowledge about a sound source is injected with
the reveal command instead.  The reveal reference records two properties this
function relies on: the knowledge value is clamped to 0..4 and set to 1 when
the revealing side holds none, and it can only rise.  This function computes
the arriving range from AEE's propagation index and reveals the source to
every live unit of an opposing side inside that range.

The reveal value stays below 1.5, the engine's side-identification threshold:
hearing tells the AI a shot happened and roughly where, but never which side
fired.

Runs where the AI is simulated (the server, or the host in a single-player
game), because reveal only updates knowledge on the machine it runs on.

Arguments:
  0: Object - the sound source, the firer

Returns:
  Number - the number of units revealed
*/

params [
    ["_source", objNull, [objNull]]
];

if (isNull _source) exitWith { 0 };

private _index = missionNamespace getVariable [QEGVAR(weather,currentSoundPropagation), 1];
if !(_index isEqualType 0) then { _index = 1; };

private _range = [AI_HEARING_BASE_RANGE, _index] call FUNC(hearingRange);
private _sourceSide = side _source;
private _sourcePos = getPos _source;
private _revealed = 0;

{
    if ((alive _x) && {((side _x) getFriend _sourceSide) < 0.6}) then {
        private _distance = _sourcePos distance _x;
        private _fraction = ((_range - _distance) / (_range max 0.001)) max 0 min 1;
        private _value = AI_HEARING_REVEAL_MIN + (_fraction * (AI_HEARING_REVEAL_MAX - AI_HEARING_REVEAL_MIN));
        _x reveal [_source, _value];
        _revealed = _revealed + 1;
    };
} forEach (nearestObjects [_sourcePos, ["CAManBase"], _range]);

_revealed
