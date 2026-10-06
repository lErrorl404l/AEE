#include "..\..\script_component.hpp"
/*
Active-IR gate kernel (pure).

Decides whether the active-IR illuminator may run.  The kernel reads no
engine state: every input is passed in, so the decision is identical on every
machine and the unit suite can execute the real SQF with fixtures.

Params:
    0: _settingOn    (BOOL) - the AEE Thermal > Sensor active-IR setting
    1: _hasInterface (BOOL) - the machine has an interface, not a dedicated server
    2: _unitNull     (BOOL) - the operator object is null
    3: _unitAlive    (BOOL) - the operator is alive

Returns: BOOL - true when the illuminator may run.
*/
params [
    ["_settingOn", false, [false]],
    ["_hasInterface", false, [false]],
    ["_unitNull", true, [false]],
    ["_unitAlive", false, [false]]
];

_settingOn && _hasInterface && !_unitNull && _unitAlive
