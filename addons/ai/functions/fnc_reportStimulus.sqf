#include "..\script_component.hpp"

/*
Report a stimulus to the other machines.

Rate limited to four events per second so the network cost is bounded.  The
event is one small array, a position, a magnitude and the current mission
time.  Every receiver applies it at the same time, so the disturbance field
stays deterministic across machines.  The broadcast excludes the caller, so the
caller applies the same payload to its own field itself.

Arguments:
  0: Array  - the stimulus position
  1: Number - the stimulus magnitude, 0 to 1

Returns:
  Nothing.
*/

params [
    ["_pos", [0, 0, 0], [[]]],
    ["_magnitude", 0.5, [0]]
];

private _now = CBA_missionTime;
private _last = missionNamespace getVariable [QGVAR(lastReport), -1e9];
if !(_last isEqualType 0) then { _last = -1e9; };

// The rate limit sits above the self-apply, not only above the broadcast, so a
// dropped event changes no field on any machine, the caller included.
if ((_now - _last) < (1 / AI_BROADCAST_RATE)) exitWith {};

missionNamespace setVariable [QGVAR(lastReport), _now];

private _payload = [_pos, _magnitude, _now];

// -2 is every machine except the origin (the caller).  The broadcast leaves the
// caller's own field untouched, so the caller applies the same payload here,
// once, or the shooter's field never holds its own gunfire.
[_payload] call FUNC(receiveStimulus);
[_payload] remoteExecCall [QFUNC(receiveStimulus), -2];
