#include "script_component.hpp"

ADDON = false;

#include "XEH_PREP.hpp"
#include "initSettings.inc.sqf"

if (is3DEN) exitWith {};

if (hasInterface) then {
    [{
        [] call FUNC(integrateTFAR);
    }, 5] call CBA_fnc_addPerFrameHandler;
};

ADDON = true;
