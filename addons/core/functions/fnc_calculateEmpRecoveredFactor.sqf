#include "..\script_component.hpp"

/*
EMP degradation factor after a recovery interval (issue #9).

The device is degraded to factor f0 at the burst, then recovers towards 1.0
with the time constant tau:

    factor(t) = 1 - (1 - f0) * exp(-t / tau)

Source: the standard first-order (exponential) recovery, applied with the
time constant fnc_calculateEmpRecovery returns.  At t = 0 the factor is f0;
as t grows it approaches 1.0.

The kernel is pure: it reads no engine state.

Arguments:
  0: f0       (NUMBER) - degradation factor at the burst, 0..1
  1: elapsedS (NUMBER) - time since the burst, seconds
  2: tauS     (NUMBER) - recovery time constant, seconds

Return Value: NUMBER - recovered degradation factor, 0..1
Example: [0.5, 0, 30] call aee_core_fnc_calculateEmpRecoveredFactor
Public: No
*/

params [
    ["_f0", 1, [0]],
    ["_elapsedS", 0, [0]],
    ["_tauS", 1, [0]]
];

if (_f0 >= 1) exitWith { 1 };

1 - ((1 - _f0) * (exp ((0 - _elapsedS) / (_tauS max 0.001))))
