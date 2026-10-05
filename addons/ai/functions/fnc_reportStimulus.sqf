#include "..\script_component.hpp"

/*
Report a stimulus to the other machines.

Rate limited to four events per second so the network cost is bounded.  The
event is one small array, a position, a magnitude and the current mission
time.  Every receiver applies it at the same time, so the disturbance field
stays deterministic across machines.

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

if ((_now - _last) < (1 / AI_BROADCAST_RATE)) exitWith {};

missionNamespace setVariable [QGVAR(lastReport), _now];

// -2 is every machine except the origin (the caller).  On a hosted server the
// local player is the origin, so the caller applies its own stimulus directly
// and the field stays consistent without a self-broadcast.
[[_pos, _magnitude, _now]] remoteExecCall [QFUNC(receiveStimulus), -2];
