#include "..\script_component.hpp"

/*
Author: AEE
Description: Rolls a deterministic chance to ignite a fire when a lightning strike is active, and publishes the strike position.
Arguments: None
Return Value: BOOL: fire ignition occurred
Example: [] call aee_fx_fnc_calculateLightningStrikeEffects
Public: No
*/

private _strikeActive = missionNamespace getVariable [QEGVAR(atmos,currentLightningStrike), false];
private _strikePos = missionNamespace getVariable [QEGVAR(atmos,lastLightningPos), []];
private _ignitionChance = missionNamespace getVariable [QGVAR(lightningIgnitionChance), 0.1];

private _ignition = false;
if (_strikeActive) then {
    _ignition = ([round (time * 10), 501] call EFUNC(core,deterministicRandom)) < _ignitionChance;
};

missionNamespace setVariable [QEGVAR(core,lightningIgnition), _ignition];
missionNamespace setVariable [QEGVAR(core,lastStrikePos), _strikePos];

_ignition
