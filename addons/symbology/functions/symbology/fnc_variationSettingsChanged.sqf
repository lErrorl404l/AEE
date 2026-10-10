#include "..\..\script_component.hpp"
/*
 * aee_symbology_fnc_variationSettingsChanged
 *
 * Rebuilds the active state from the CBA LIST settings and applies it.  The
 * settings are the source of truth: the selector dialog writes through to them,
 * so a change re-types the placed AEE_Variation markers live.  Called by each
 * variation setting's change handler.
 *
 * Return: nothing.
 */
private _state = [
    ["affiliation", missionNamespace getVariable [QGVAR(variationAffiliation), "friend"]],
    ["dimension", missionNamespace getVariable [QGVAR(variationDimension), "land"]],
    ["function", missionNamespace getVariable [QGVAR(variationFunction), "infantry"]],
    ["echelon", missionNamespace getVariable [QGVAR(variationEchelon), "team"]],
    ["palette", missionNamespace getVariable [QGVAR(variationPalette), "NATO"]]
];
missionNamespace setVariable [QGVAR(variationState), _state];
[] call FUNC(variationApply);
