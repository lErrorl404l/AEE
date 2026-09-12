#include "script_component.hpp"

ADDON = false;

#include "XEH_PREP.hpp"

if (is3DEN) exitWith {};

// Runs on every machine. weather.json is a file in the mission folder, so
// every machine reads identical data and publishes identical aee_core_*
// state — no publicVariable needed. One-shot: the real values are static
// for the mission, and once applied the flag gates AEE's simulation tick.
[{
    [] call FUNC(integrateRealWeather);
}, 5] call CBA_fnc_waitAndExecute;

ADDON = true;
