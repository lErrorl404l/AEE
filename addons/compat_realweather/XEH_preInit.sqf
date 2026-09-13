#include "script_component.hpp"

ADDON = false;

#include "XEH_PREP.hpp"
#include "initSettings.inc.sqf"

if (is3DEN) exitWith {};

// Runs on every machine when enabled.  weather.json is a file in the
// mission folder, so every machine reads identical data and publishes
// identical aee_core_* state — no publicVariable needed. One-shot: the
// real values are static for the mission, and once applied the flag
// gates AEE's simulation tick.
// loadFile logs "weather.json not found" when the file is absent — that
// only happens when the user enables real weather without providing the
// file, which is the correct moment to warn.
if (GVAR(enabled)) then {
    [{
        [] call FUNC(integrateRealWeather);
    }, 5] call CBA_fnc_waitAndExecute;
};

ADDON = true;
