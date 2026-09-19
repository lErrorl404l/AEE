#include "..\..\script_component.hpp"

/*
Water temperature with thermal inertia (leaky integrator).

First-order low-pass filter: each tick retains 95 % of the previous value,
mixing in 5 % of the current air temperature.  At a 5 s tick this gives
an effective time constant of ~100 s — water masses change slowly.

  waterTemp = (prevWaterTemp × 0.95) + (airTemp × 0.05)

Initialises from air temperature on first call.

Stored in GVAR(currentWaterTemperature).
*/

private _T_C = missionNamespace getVariable [QEGVAR(core,currentTemperature), 15];
if !(_T_C isEqualType 0) then { _T_C = 15; };

private _prevWaterTemp = missionNamespace getVariable [QEGVAR(core,currentWaterTemperature), _T_C];
private _waterTemp = (_prevWaterTemp * 0.95) + (_T_C * 0.05);

missionNamespace setVariable [QEGVAR(core,currentWaterTemperature), _waterTemp];

_waterTemp
