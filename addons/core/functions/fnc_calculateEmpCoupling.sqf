#include "..\script_component.hpp"

/*
EMP field coupling through a hardening barrier (issue #9).

A shield attenuates the free field by its shielding effectiveness in dB:

    E_coupled = E_free * 10^(-dB / 20)

Source: the issue's coupling model.  The 20 is the field (not power) dB
convention: field amplitude ratio = 10^(-dB/20).  A 20 dB soft-skin vehicle
turns a 50 kV/m free field into 5 kV/m at the electronics.

Hardening values (issue #9, from MIL-STD-188-125 and CISA):
  civilian      0 dB
  radio         0 dB
  soft vehicle 20 dB
  armoured     40 dB
  facility     80 dB (MIL-STD-188-125 welded steel, CISA level 4)

The kernel is pure: it reads no engine state.

Arguments:
  0: freeVpm    (NUMBER) - free field, V/m
  1: hardeningDB (NUMBER) - shielding effectiveness, dB (>= 0)

Return Value: NUMBER - coupled field, V/m
Example: [50000, 20] call aee_core_fnc_calculateEmpCoupling
Public: No
*/

params [
    ["_freeVpm", 0, [0]],
    ["_hardeningDB", 0, [0]]
];

_freeVpm * (10 ^ ((0 - _hardeningDB) / 20))
