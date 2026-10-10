#include "..\script_component.hpp"
/*
Coolant temperature under the engine heat balance (issue #111).

  C * dT/dt = Q_reject - UA * (T - T_ambient)

The equilibrium is T_inf = T_ambient + Q_reject / UA, and the exact exponential
solution over an interval dt is

  T' = T_inf + (T - T_inf) * exp(-dt / tau),   tau = C / UA

so the result does not depend on the tick interval.  This is the SAME
first-order lag and the SAME exact-exponential step the existing vehicle
thermal kernel aee_thermal_fnc_calculateVehicleHeat integrates, and UA is the
SAME Holman flat-plate air correlation that kernel uses, h = 5.6 + 3.9 v times
the surface area.  The two kernels answer different questions: the thermal
kernel returns the engine BODY heat fraction for the infrared display; this
kernel returns the COOLANT temperature for the power derate.  They share the
correlation and the integration form, and neither re-derives the other.

THE CONDUCTANCE AND THE TIME CONSTANT ARE THE CALLER'S.  The caller builds UA
from the Holman correlation and the surface area, and passes the coolant time
constant.  This kernel is pure arithmetic over scalars.

Guards, each explicit:
  - A non-positive UA is refused: the equilibrium divides by it, and no
    conductance means no equilibrium.  The current temperature is returned.
  - A non-positive time constant is refused: the lag divides by it.  The
    current temperature is returned.
  - A negative interval is refused: time does not run backward.  The current
    temperature is returned.

Arguments:
  0: _tAmbientC  (NUMBER) ambient air temperature, C
  1: _qRejectW   (NUMBER) heat rejected to the coolant, W
  2: _uaW        (NUMBER) overall conductance h*A, W/K, > 0
  3: _tauS       (NUMBER) coolant time constant, s, > 0
  4: _tCoolantC  (NUMBER) current coolant temperature, C
  5: _deltaTimeS (NUMBER) elapsed interval, s, >= 0

Return Value: NUMBER - the coolant temperature after the interval, C.
Example: [15, 40000, 800, 90, 90, 5] call aee_vehicles_fnc_calculateCoolantTemperature
Public: No
*/

params [
    ["_tAmbientC", 15, [0]],
    ["_qRejectW", 0, [0]],
    ["_uaW", 0, [0]],
    ["_tauS", 0, [0]],
    ["_tCoolantC", 15, [0]],
    ["_deltaTimeS", 0, [0]]
];

if (_uaW <= 0) exitWith { _tCoolantC };
if (_tauS <= 0) exitWith { _tCoolantC };
if (_deltaTimeS < 0) exitWith { _tCoolantC };

private _tInf = _tAmbientC + (_qRejectW / _uaW);
private _tNew = _tInf + ((_tCoolantC - _tInf) * exp (-(_deltaTimeS / _tauS)));

_tNew
