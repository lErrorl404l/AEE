#include "..\..\script_component.hpp"
/*
 * aee_optics_fnc_symbologyDimension
 *
 * Pure dimension kernel.  Maps a class category to its battle dimension,
 * using the generated dimension table aee_optics_symbologyTables.  PURE: the
 * category arrives as an argument and the table is loaded data, so the
 * kernel reads no marker, no unit and no world.
 *
 * The dimension table is section 6.  Each row is
 * [categoryName, dimension, grade, source].  A category with no row returns
 * "land", the APP-6(C) default frame.
 *
 * Arguments:
 *   0: _category <STRING> a class category, for example "rotary"
 *
 * Return: <STRING> a dimension token, for example "air".
 */
params [
    ["_category", "unknown", [""]]
];

private _tables = aee_optics_symbologyTables;
private _dimensions = _tables select 6;

private _dimension = "land";
private _found = false;
for "_i" from 0 to ((count _dimensions) - 1) do {
    if (!_found && (_category isEqualTo ((_dimensions select _i) select 0))) then {
        _dimension = (_dimensions select _i) select 1;
        _found = true;
    };
};

_dimension
