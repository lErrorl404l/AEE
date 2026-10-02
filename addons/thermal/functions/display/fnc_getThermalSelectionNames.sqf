#include "..\..\script_component.hpp"
/*
 * Thermal selection names (issue #204).
 *
 * fnc_getThermalSelections returns selection INDICES.  The local heat
 * sources need selection NAMES: a name is what fnc_applySelectionThermal
 * takes, what the hit-point material map is keyed by, and what
 * fnc_getThermalSelectionPoints resolves to a model point.  This function
 * is the one index-to-name mapping, so the four sources do not each repeat
 * it and cannot disagree on the order.
 *
 * Params:
 *   0: _object (OBJECT)
 *
 * Returns: ARRAY of STRING - the names of the object's thermal selections,
 *   in the order fnc_getThermalSelections returned them.  An index that
 *   does not name a model selection is dropped.
 */
params [["_object", objNull, [objNull]]];

if (isNull _object) exitWith { [] };

private _sels = [_object] call FUNC(getThermalSelections);
if (_sels isEqualTo []) exitWith { [] };

private _allNames = selectionNames _object;
private _names = [];
{
    if ((_x isEqualType 0) && (_x >= 0) && (_x < count _allNames)) then {
        _names pushBack (_allNames select _x);
    };
} forEach _sels;

_names
