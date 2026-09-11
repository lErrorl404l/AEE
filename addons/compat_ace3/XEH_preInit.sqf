#include "script_component.hpp"

ADDON = false;

#include "XEH_PREP.hpp"

if (is3DEN) exitWith {};

// AEE sets engine weather directly (setWind, setFog, setOvercast). Disable
// ACE3's own weather simulation so the two models do not fight. ACE3's
// weather module reads engine state, so it follows AEE automatically.
if (isClass (configFile >> "CfgPatches" >> "ace_weather")) then {
    ace_weather_windSimulation = false;
    ace_weather_enableWind      = false;
    ace_weather_enableRain      = false;
    ace_weather_enableFog       = false;
    ace_weather_enableOvercast  = false;
    diag_log "[AEE][ACE3 Compat] ACE3 weather simulation disabled - AEE controls engine weather";
};

if (hasInterface) then {
    [{
        call FUNC(integrateMedical);
    }, 5] call CBA_fnc_addPerFrameHandler;
};

ADDON = true;
