#include "..\script_component.hpp"

/*
Battery capacity derating factor (0.3–1.0) for temperature extremes.

Lithium-based batteries lose capacity in cold (reduced electrochemistry)
and slightly in extreme heat.  The derating factor is a multiplier
applied to rated capacity.

  • Below –10 °C: linear reduction capped at –0.7 (from 1.0)
  • Above +45 °C: slight linear reduction capped at –0.2
  • Normal range: 1.0 (full rated capacity)

Stored in GVAR(batteryTemperatureDerating).
*/

params [];

private _temp = EGVAR(core,currentTemperature);
if (isNil "_temp") exitWith { 1.0 };

private _factor = 1.0;

if (_temp < -10) then {
    _factor = _factor - (((-10 - _temp) * 0.015) min 0.7);
};

if (_temp > 45) then {
    _factor = _factor - (((_temp - 45) * 0.01) min 0.2);
};

_factor = (_factor max 0.3) min 1.0;

missionNamespace setVariable [QGVAR(batteryTemperatureDerating), _factor];

_factor
