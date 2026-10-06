#include "script_component.hpp"

AEE_MODULE_PRE_INIT

ADDON = false;

#include "XEH_PREP.hpp"
#include "initSettings.inc.sqf"

if (is3DEN) exitWith {};

if (hasInterface) then {
    [{
        private _perfT0 = diag_tickTime;
        [ACE_player] call FUNC(integrateACM);
        if (AEE_TRACE_ON) then {
            private _perfMsg = format ["integrateACM %1 ms", round ((diag_tickTime - _perfT0) * 1000)];
            AEE_LOG_DEBUG(_perfMsg);
        };
    }, 5] call CBA_fnc_addPerFrameHandler;
};

// One-shot registration of the optional hypoxia duty factor (all machines)
call FUNC(registerHypoxiaDutyFactor);

ADDON = true;
