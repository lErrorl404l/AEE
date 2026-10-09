#include "..\script_component.hpp"

/*
Disturbance-silence kernel (wildlife ecology).

Pure: no missionNamespace, no GVAR or EGVAR, no engine command.  Maps the
disturbance at the listener to a 0 to 1 gain multiplier for the ambient bed.
A quiet area keeps gain 1.  A fully disturbed area goes silent.

Arguments:
  0: Number - the disturbance at the listener, 0 to 1
  1: Number - the decay strength, the silenceDecay setting

Returns:
  Number - the gain multiplier, 0 to 1
*/

params [
    ["_disturbance", 0, [0]],
    ["_decay", 0.05, [0]]
];

private _dist = ((_disturbance max 0) min 1);
private _decayClamped = (_decay max 0);
private _silence = (_dist * _decayClamped * 20) min 1;

(1 - _silence)
