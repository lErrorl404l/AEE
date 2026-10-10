#include "..\..\script_component.hpp"
/*
 * aee_symbology_fnc_variationDialogRefresh
 *
 * Rebuilds the selector rows from the model.  One row per option, one button
 * per value, the active value highlighted.  The rows are built from
 * FUNC(variationOptions), so a new option value appears with no UI change.
 * Called from the display onLoad and, deferred, after a selection.
 *
 * The clear (ctrlDelete) runs here, never from a control's own event handler:
 * ctrlDelete inside a control's own handler crashes the engine.
 *
 * Arguments:
 *   0: _display <DISPLAY> the selector display (defaults to the stored one)
 *
 * Return: nothing.
 */
params [["_display", displayNull, [displayNull]]];
if (isNull _display) then {
    _display = uiNamespace getVariable [QGVAR(variationDisplay), displayNull];
};
if (isNull _display) exitWith {};

private _families = call FUNC(variationFamilies);
private _family = "symbol";
private _familyLabel = "";
if (_families isNotEqualTo []) then {
    _family = (_families select 0) select 0;
    _familyLabel = (_families select 0) select 1;
};
(_display displayCtrl 1201) ctrlSetText _familyLabel;

private _options = [_family] call FUNC(variationOptions);
private _state = missionNamespace getVariable [QGVAR(variationState), []];
private _group = _display displayCtrl 1202;
{
    ctrlDelete _x;
} forEach (allControls _group);

private _rowH = 0.05 * safeZoneH;
private _labelW = 0.13 * safeZoneW;
private _buttonW = 0.075 * safeZoneW;
private _gap = 0.004 * safeZoneW;
{
    private _option = _x;
    private _rowY = _forEachIndex * _rowH;
    private _optionId = _option select 0;
    private _values = _option select 2;
    private _active = "";
    {
        if ((_x select 0) isEqualTo _optionId) then { _active = _x select 1; };
    } forEach _state;

    private _label = _display ctrlCreate ["RscText", -1, _group];
    _label ctrlSetPosition [0, _rowY, _labelW, _rowH];
    _label ctrlSetText (_option select 1);
    _label ctrlCommit 0;

    private _bx = _labelW;
    {
        private _value = _x;
        private _button = _display ctrlCreate ["RscButton", -1, _group];
        _button ctrlSetPosition [_bx, _rowY, _buttonW, _rowH];
        _button ctrlSetText (_value select 1);
        if ((_value select 0) isEqualTo _active) then {
            _button ctrlSetBackgroundColor [0.20, 0.50, 0.20, 1];
        } else {
            _button ctrlSetBackgroundColor [0.15, 0.15, 0.15, 1];
        };
        _button ctrlAddEventHandler ["ButtonClick", format [
            "['%1', '%2'] call aee_symbology_fnc_variationDialogSelect", _optionId, _value select 0
        ]];
        _button ctrlCommit 0;
        _bx = _bx + _buttonW + _gap;
    } forEach _values;
} forEach _options;

private _rowsH = (count _options) * _rowH;
private _groupPos = ctrlPosition _group;
_group ctrlSetPosition [_groupPos select 0, _groupPos select 1, _groupPos select 2, _rowsH];
_group ctrlCommit 0;
