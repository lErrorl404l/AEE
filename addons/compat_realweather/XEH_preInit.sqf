#include "script_component.hpp"

ADDON = false;

#include "XEH_PREP.hpp"

// Register the settings only when the mission provides weather.json.
// CBA has no way to hide a registered setting at runtime, so the settings
// must not register at all when the feature is unused — otherwise "AEE
// Real Weather" appears in the options menu even though nothing can use it
// (the same visibility rule as a host-mod addon whose dependency is absent).
// loadFile works at preInit: an empty result means no weather.json.
private _jsonPresent = (loadFile "weather.json") != "";
if (_jsonPresent) then {
    #include "initSettings.inc.sqf"
};

if (is3DEN) exitWith {};

// Runs on every machine when enabled.  weather.json is a file in the
// mission folder, so every machine reads identical data and publishes
// identical aee_core_* state — no publicVariable needed. One-shot: the
// real values are static for the mission, and once applied the flag
// gates AEE's simulation tick.
// The setting (default off) prevents loadFile from logging "weather.json
// not found" when the user is not using real-weather mode.
if (_jsonPresent && (missionNamespace getVariable [QGVAR(enabled), false])) then {
    [{
        [] call FUNC(integrateRealWeather);
    }, 5] call CBA_fnc_waitAndExecute;
};

ADDON = true;
