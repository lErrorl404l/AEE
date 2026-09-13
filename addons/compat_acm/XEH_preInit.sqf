#include "script_component.hpp"

ADDON = false;

#include "XEH_PREP.hpp"
#include "initSettings.inc.sqf"

if (is3DEN) exitWith {};

if (hasInterface) then {
    [{
        [ACE_player] call FUNC(integrateACM);
    }, 5] call CBA_fnc_addPerFrameHandler;
};

// One-shot registration of the optional hypoxia duty factor (all machines)
call FUNC(registerHypoxiaDutyFactor);

ADDON = true;
