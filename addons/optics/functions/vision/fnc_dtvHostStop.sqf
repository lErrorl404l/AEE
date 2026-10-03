#include "..\..\script_component.hpp"

/*
Stop the DTV base-channel host driver and restore the native TI.

Idempotent.  The fnc_updateThermalHost call restores the tracked vehicle's
disableTIEquipment and runs the thermal sensor EXIT once.
*/
if (isNil QGVAR(dtvHostPFH)) exitWith {};
[GVAR(dtvHostPFH)] call CBA_fnc_removePerFrameHandler;
GVAR(dtvHostPFH) = nil;
[] call FUNC(updateThermalHost);
AEE_LOG_INFO("DTV thermal host PFH stopped");
