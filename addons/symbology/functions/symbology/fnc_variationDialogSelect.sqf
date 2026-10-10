#include "..\..\script_component.hpp"
/*
 * aee_symbology_fnc_variationDialogSelect
 *
 * Selects a value for one option.  The CBA LIST settings are the source of
 * truth: the dialog writes through to the option's setting, whose change
 * handler rebuilds the active state and re-types the markers, so the dialog and
 * the settings never diverge.  An unknown option id updates the state directly.
 * The rebuild is DEFERRED with CBA_fnc_waitAndExecute, because ctrlDelete inside
 * a control's own event handler crashes the engine.
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

private _optionIds = ["affiliation", "dimension", "function", "echelon", "palette"];
private _keys = ["variationAffiliation", "variationDimension", "variationFunction", "variationEchelon", "variationPalette"];
private _index = _optionIds find _optionId;
if (_index >= 0) then {
    [format ["aee_symbology_%1", _keys select _index], _valueId, 0, "client", true] call CBA_settings_fnc_set;
} else {
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
};

[{
    private _display = uiNamespace getVariable [QGVAR(variationDisplay), displayNull];
    [_display] call FUNC(variationDialogRefresh);
}, [], 0] call CBA_fnc_waitAndExecute;
