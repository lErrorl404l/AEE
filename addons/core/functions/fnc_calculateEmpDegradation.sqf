#include "..\script_component.hpp"

/*
EMP device degradation factor from the coupled field (issue #9).

A coupled field above a device's upset threshold degrades it.  The severity
ratio the model uses is the coupled field over the device DAMAGE threshold,
which is the same ratio the issue's recovery formula uses:

    r = E_coupled / E_damage

The degradation factor is a monotone model mapping of that ratio:

    factor = 1 / (1 + r)

This is a MODEL MAPPING, not a published law: no source states a device
response curve, so the code does not invent one.  It is continuous and needs
no invented constant: at zero field the factor is 1.0 (no effect), at the
damage threshold it is 0.5, and it falls towards zero as the field rises.

Device thresholds (issue #9; upset / damage, from the EMP Commission 2008 and
the DOE HEMP literature):
  optoelectronics     1 / 5 kV/m
  comms (handheld)    2 / 10 kV/m
  vehicle electronics 5 / 25 kV/m

The kernel is pure: it reads no engine state.

Arguments:
  0: coupledVpm (NUMBER) - coupled field at the device, V/m
  1: damageVpm  (NUMBER) - device damage threshold, V/m (default 5000)

Return Value: NUMBER - degradation factor, 1.0 (intact) to ~0 (destroyed)
Example: [5000, 5000] call aee_core_fnc_calculateEmpDegradation
Public: No
*/

params [
    ["_coupledVpm", 0, [0]],
    ["_damageVpm", 5000, [0]]
];

private _r = _coupledVpm / (_damageVpm max 1);

1 / (1 + _r)
