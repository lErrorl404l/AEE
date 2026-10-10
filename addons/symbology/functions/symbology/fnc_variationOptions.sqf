#include "..\..\script_component.hpp"
/*
 * aee_symbology_fnc_variationOptions
 *
 * Pure variation-options kernel.  Lists one family's options and their derived
 * values.  PURE: the family id arrives as an argument and the family table is
 * loaded data, so the kernel reads no marker, no unit, no setting and no
 * world.  A family the table does not hold returns an empty list.
 *
 * Arguments:
 *   0: _familyId <STRING> the family id, for example "symbol"
 *
 * Return: <ARRAY> [[optionId, label, [[valueId, label, token], ...]], ...].
 */
params [
    ["_familyId", "", [""]]
];

private _families = aee_symbology_variationFamilies;
private _options = [];
private _found = false;
for "_i" from 0 to ((count _families) - 1) do {
    if (!_found && (_familyId isEqualTo ((_families select _i) select 0))) then {
        _options = (_families select _i) select 5;
        _found = true;
    };
};

private _out = [];
{
    private _option = _x;
    private _values = [];
    for "_j" from 0 to ((count (_option select 3)) - 1) do {
        private _value = (_option select 3) select _j;
        _values pushBack [(_value select 0), (_value select 1), (_value select 2)];
    };
    _out pushBack [(_option select 0), (_option select 1), _values];
} forEach _options;

_out
