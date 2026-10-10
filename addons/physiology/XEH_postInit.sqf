#include "script_component.hpp"
#include "\z\aee\addons\lib\script_debug.hpp"

AEE_MODULE_POST_INIT

// A new body has no heat acclimatisation or altitude adaptation.  The
// acclimatisation state is owned by aee_altitude and published under its
// name, so reset it there.
["AEE_OnPlayerKilled", {
    params ["_unit", "_killer", "_instigator", "_useEffects"];
    missionNamespace setVariable [QEGVAR(altitude,acclimatizationPercent), 0];
}] call CBA_fnc_addPlayerKilledHandler;

// Uniform per-module state dump, one line a second.
[FUNC(dumpState), 1] call CBA_fnc_addPerFrameHandler;

// Survival pressure (will to live): one read a second, at the state tick,
// never per frame.  Publishes aee_physiology_survivalPressure for the AI.
[FUNC(survivalState), 1] call CBA_fnc_addPerFrameHandler;
