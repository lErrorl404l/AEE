#include "..\..\script_component.hpp"

/*
Start the rain-scaled weather-grain PFH (aee-workshop-copy item 5).

Client-only.  Idempotent: a second call does nothing while the PFH is live.
The 1.0 s tick refreshes the grain parameters from rain and sunOrMoon and
applies the hysteresis.  The visionMode event does not need a special path:
the driver stands down on its own tick when a sensor mode is active.

Arguments: none.

Returns:
  Nothing.
*/

if (!hasInterface) exitWith {};
if (!isNil QGVAR(weatherGrainPFH)) exitWith {};

GVAR(weatherGrainPFH) = [FUNC(applyWeatherGrain), 1.0] call CBA_fnc_addPerFrameHandler;

AEE_LOG_INFO("weather grain PFH started")
