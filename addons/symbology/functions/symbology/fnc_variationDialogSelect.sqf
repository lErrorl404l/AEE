#include "..\..\script_component.hpp"
/*
 * aee_symbology_fnc_variationDialogSelect
 *
 * Selects a value for one option: updates the active state, applies it to the
 * markers, and rebuilds the rows.  The rebuild is DEFERRED with
 * CBA_fnc_waitAndExecute, because ctrlDelete inside a control's own event
 * handler crashes the engine.
 *
 * Arguments:
 *   0: _optionId <STRING> the option id
 *   1: _valueId  <STRING> the value id
 *
 * Return: nothing.
 */
params [
    ["_optionId", "", [""]],
    ["_valueId", "", [""]]
];

private _state = missionNamespace getVariable [QGVAR(variationState), []];
private _found = false;
{
    if ((_x select 0) isEqualTo _optionId) then {
        _x set [1, _valueId];
        _found = true;
    };
} forEach _state;
if (!_found) then {
    _state pushBack [_optionId, _valueId];
};
missionNamespace setVariable [QGVAR(variationState), _state];

[] call FUNC(variationApply);

[{
    private _display = uiNamespace getVariable [QGVAR(variationDisplay), displayNull];
    [_display] call FUNC(variationDialogRefresh);
}, [], 0] call CBA_fnc_waitAndExecute;
