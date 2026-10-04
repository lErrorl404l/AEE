#include "..\script_component.hpp"

/*
Stop the wildlife client tick and release its sound source.

Arguments: none.

Returns:
  Nothing.
*/

if (!isNil QGVAR(ambientPFH)) then {
    [GVAR(ambientPFH)] call CBA_fnc_removePerFrameHandler;
    GVAR(ambientPFH) = nil;
};

private _source = missionNamespace getVariable [GVAR(ambientSource), objNull];
if (!isNull _source) then {
    deleteVehicle _source;
    missionNamespace setVariable [GVAR(ambientSource), objNull];
};

AEE_LOG_INFO("wildlife client tick stopped")
