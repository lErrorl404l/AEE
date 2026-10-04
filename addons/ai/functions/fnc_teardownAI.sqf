#include "..\script_component.hpp"

/*
Stop the reusable substrate client tick.

Arguments: none.

Returns:
  Nothing.
*/

if (!isNil QGVAR(aiPFH)) then {
    [GVAR(aiPFH)] call CBA_fnc_removePerFrameHandler;
    GVAR(aiPFH) = nil;
};

AEE_LOG_INFO("ai substrate PFH stopped")
