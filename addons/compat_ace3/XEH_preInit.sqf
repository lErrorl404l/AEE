#include "script_component.hpp"

ADDON = false;

#include "XEH_PREP.hpp"

if (is3DEN) exitWith {};

// AEE owns the weather state. Disable ACE3's own weather simulation so the
// two models do not fight. Verified against ACE3 source: ace_weather_enabled
// gates the server update tick (XEH_postServerInit); the enableWind/Rain/Fog/
// Overcast settings below are NOT read by any ACE3 code (dead settings), so
// ace_weather_enabled = false is the effective stop.
if (isClass (configFile >> "CfgPatches" >> "ace_weather")) then {
    ace_weather_enabled       = false;
    ace_weather_windSimulation = false;
    ace_weather_enableWind      = false;
    ace_weather_enableRain      = false;
    ace_weather_enableFog       = false;
    ace_weather_enableOvercast  = false;
    diag_log "[AEE][ACE3 Compat] ACE3 weather simulation disabled - AEE controls weather state";
};

// Runs on every machine (server and clients): the weather state must be
// written wherever ACE3 consumers read it.  AEE state is deterministic, so
// each machine computes identical values.  Medical integration needs a
// local unit, so it stays gated on hasInterface.
[{
    [] call FUNC(integrateKestrel);
}, 5] call CBA_fnc_addPerFrameHandler;

if (hasInterface) then {
    [{
        [] call FUNC(integrateMedical);
    }, 5] call CBA_fnc_addPerFrameHandler;
};

ADDON = true;
