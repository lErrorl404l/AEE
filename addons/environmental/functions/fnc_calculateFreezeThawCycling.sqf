#include "..\script_component.hpp"

/*
Freeze-thaw ground state with hysteresis to avoid rapid oscillation at 0 °C.

Maintains a continuous state variable QGVAR(freezeThawState):
  +1.0  fully thawed
   0.0  transition midpoint
  –1.0  frozen solid

Freezing rate scales with how far below –1 °C the temperature is;
thawing rate scales with how far above +1 °C.  The –1 to +1 hysteresis
zone prevents chattering.

Also sets a human-readable description in QGVAR(freezeThawDescription).
*/

params [];

private _temp = EGVAR(core,currentTemperature);
if (isNil "_temp") exitWith {
    missionNamespace setVariable [QGVAR(freezeThawState), 1.0];
    missionNamespace setVariable [QGVAR(freezeThawDescription), "Thawed"];
    1.0
};

private _interval = GVAR(updateInterval);
private _state    = missionNamespace getVariable [QGVAR(freezeThawState), 1.0];

private _delta = 0;

if (_temp < -1) then {
    _delta = -0.02 * (-1 - _temp) * (_interval / 5);
};

if (_temp > 1) then {
    _delta = 0.02 * (_temp - 1) * (_interval / 5);
};

_state = (_state + _delta) max -1 min 1;

// ─── Human-readable description ────────────────────────────────────────
private _description = switch (true) do {
    case (_state > 0.5):  { "Thawed" };
    case (_state > 0):    { "Partially Thawed" };
    case (_state > -0.5): { "Partially Frozen" };
    default               { "Frozen" };
};

missionNamespace setVariable [QGVAR(freezeThawState), _state];
missionNamespace setVariable [QGVAR(freezeThawDescription), _description];

_state
