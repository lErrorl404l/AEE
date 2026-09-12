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

Also accumulates freezing/thawing degree-days and derives freeze/thaw
depth from the Stefan solution — depth is proportional to
sqrt(accumulated degree-days), so a warm spell melts fast initially then
slows (physically correct).

Stores:
  QGVAR(freezeThawState)          — +1 thawed ... –1 frozen
  QGVAR(freezeThawDescription)    — human-readable description
  QEGVAR(core,frozenDepth_m)      — Stefan freeze depth
  QEGVAR(core,thawDepth_m)        — Stefan thaw depth
*/

params [];

private _temp = EGVAR(core,currentTemperature);
if (isNil "_temp") exitWith {
    missionNamespace setVariable [QGVAR(freezeThawState), 1.0];
    missionNamespace setVariable [QGVAR(freezeThawDescription), "Thawed"];
    1.0
};

private _interval = missionNamespace getVariable [QEGVAR(core,updateInterval), 5];
private _state    = missionNamespace getVariable [QGVAR(freezeThawState), 1.0];

// ─── Degree-day accumulation (Stefan solution) ────────────────────────────
private _FDD = missionNamespace getVariable [QEGVAR(core,freezingDegreeDays), 0];
private _TDD = missionNamespace getVariable [QEGVAR(core,thawingDegreeDays), 0];
_FDD = _FDD + ((0 - _temp) max 0) * (_interval / 86400);
_TDD = _TDD + ((_temp - 0) max 0) * (_interval / 86400);
missionNamespace setVariable [QEGVAR(core,freezingDegreeDays), _FDD];
missionNamespace setVariable [QEGVAR(core,thawingDegreeDays), _TDD];

// ─── Stefan freeze/thaw depth — proportional to sqrt(degree-days) ─────────
// 0.05 m per sqrt(degC-day), typical for silty soil
private _frozenDepth_m = 0.05 * (sqrt _FDD);
private _thawDepth_m   = 0.05 * (sqrt _TDD);

// ─── Hysteresis state ─────────────────────────────────────────────────────
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
missionNamespace setVariable [QEGVAR(core,frozenDepth_m), _frozenDepth_m];
missionNamespace setVariable [QEGVAR(core,thawDepth_m), _thawDepth_m];

_state
