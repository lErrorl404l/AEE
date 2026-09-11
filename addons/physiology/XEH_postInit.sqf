#include "script_component.hpp"

// A new body has no heat acclimatisation or altitude adaptation.
["AEE_OnPlayerKilled", {
    params ["_unit", "_killer", "_instigator", "_useEffects"];
    missionNamespace setVariable [QGVAR(acclimatizationPercent), 0];
}] call CBA_fnc_addPlayerKilledHandler;
