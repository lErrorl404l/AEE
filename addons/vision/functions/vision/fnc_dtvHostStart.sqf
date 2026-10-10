#include "..\..\script_component.hpp"

/*
Start the DTV base-channel host driver.

Does nothing unless the base channel setting is DTV.  Called at postInit and
from the setting's change callback, so a change to DTV takes effect without a
mission restart.
*/
if (!isNil QGVAR(dtvHostPFH)) exitWith {};
if (!hasInterface) exitWith {};
if ((missionNamespace getVariable [QEGVAR(thermal,thermalBaseChannel), 0]) != 1) exitWith {};
GVAR(dtvHostPFH) = [FUNC(dtvHostTick), 0.1] call CBA_fnc_addPerFrameHandler;
AEE_LOG_INFO("DTV thermal host PFH started");
