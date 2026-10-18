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

Forgetting is the engine's, not AEE's, so AEE never calls forgetTarget.  The
command reference (acemod/arma3-wiki 2.22, knowsAbout) states that losing sight
of a target for more than 120 seconds resets its knowsAbout to zero, and that
knowledge also resets as soon as the target leaves the view distance.  AEE
relies on that reset and does not add a second one.  forgetTarget would not be a
safe substitute: it resets ALL the information a group holds about a target and
forces knowsAbout to zero for the whole group, so a blind call would erase the
engine's own contact, including a visual one the AI legitimately holds
(arma3-wiki 2.22, forgetTarget: argument local, effect global).  The instruction
in the command reference to call forgetTarget before lowering a value does not
arise here, because this function never lowers: it injects the same band on
every heard shot, and the engine keeps the highest value.

The scan below is rate limited by AI_HEARING_SCAN_RATE.  A shot inside the
window is skipped: reveal only raises knowledge, so the next due shot re-issues
the same band while the source keeps firing.

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

private _now = CBA_missionTime;
private _lastScan = missionNamespace getVariable [QGVAR(lastSoundScan), -1e9];
if !(_lastScan isEqualType 0) then { _lastScan = -1e9; };

if !([_now, _lastScan, AI_HEARING_SCAN_RATE] call FUNC(hearingScanDue)) exitWith { 0 };

GVAR(lastSoundScan) = _now;

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
