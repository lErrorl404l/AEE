#include "..\script_component.hpp"

/*
EMP device recovery time constant (issue #9).

An upset device recovers with a time constant that grows with the severity of
the coupled field:

    tau = 1 + 29 * (E_coupled / E_damage)

Source: the issue's recovery model.  The severity ratio is the same one
fnc_calculateEmpDegradation uses, so the degradation and its recovery cannot
disagree.  A weak coupling recovers in about a second; a field at the damage
threshold recovers in 30 s; a much stronger field takes proportionally longer.

The kernel is pure: it reads no engine state.

Arguments:
  0: coupledVpm (NUMBER) - coupled field at the device, V/m
  1: damageVpm  (NUMBER) - device damage threshold, V/m (default 5000)

Return Value: NUMBER - recovery time constant, seconds (>= 1)
Example: [5000, 5000] call aee_core_fnc_calculateEmpRecovery
Public: No
*/

params [
    ["_coupledVpm", 0, [0]],
    ["_damageVpm", 5000, [0]]
];

private _r = _coupledVpm / (_damageVpm max 1);

1 + 29 * _r
