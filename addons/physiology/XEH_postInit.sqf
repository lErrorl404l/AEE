#include "script_component.hpp"

// A new body has no heat acclimatisation or altitude adaptation.
["AEE_OnPlayerKilled", {
    params ["_unit", "_killer", "_instigator", "_useEffects"];
    missionNamespace setVariable [QGVAR(acclimatizationPercent), 0];
}] call CBA_fnc_addPlayerKilledHandler;

// Register the shooter-stability sway factor with ACE3 when present.
// Runs after all addons have registered their factors; ACE3's sway loop
// picks it up on its next 0.5 s tick.
[] call FUNC(integrateSwayFactor);
