#include "script_component.hpp"

AEE_MODULE_PRE_INIT

ADDON = false;

#include "XEH_PREP.hpp"
#include "initSettings.inc.sqf"

if (is3DEN) exitWith {};

if (hasInterface) then {
    [{
        private _perfT0 = diag_tickTime;
        [] call FUNC(integrateTFAR);
        private _perfMsg = format ["integrateTFAR %1 ms", round ((diag_tickTime - _perfT0) * 1000)];
        AEE_LOG_DEBUG(_perfMsg);
    }, 5] call CBA_fnc_addPerFrameHandler;
};

ADDON = true;
