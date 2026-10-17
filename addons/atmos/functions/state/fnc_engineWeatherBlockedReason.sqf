#include "..\..\script_component.hpp"

/*
Why AEE must not write the engine weather, or "" when it may (issue #155).

Precedence.  First match wins:

  1. "setting"      the aee_atmos_engineWeatherEnabled setting is off.
  2. "manual"       aee_atmos_manualWeather is true: an operator or a mission
                    has taken manual control of the weather, so AEE must not
                    fight it.

Return: STRING, the blocking reason, or "" when AEE may write.
Public: No
*/

if (!(missionNamespace getVariable [QGVAR(engineWeatherEnabled), true])) exitWith { "setting" };

if (missionNamespace getVariable [QGVAR(manualWeather), false]) exitWith { "manual" };

""
