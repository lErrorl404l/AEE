#include "..\..\script_component.hpp"
/*
 * aee_optics_fnc_symbologyUnitDimension
 *
 * Engine adapter.  Reads a unit's class category and maps it to its battle
 * dimension through the pure kernel FUNC(symbologyDimension).  The category
 * comes from FUNC(symbologyUnitCategory), so both the frame and the
 * dimension derive from one engine read.
 *
 * Arguments:
 *   0: _unit <OBJECT> the unit object
 *
 * Return: <STRING> a dimension token, for example "air".
 */
params [
    ["_unit", objNull, [objNull]]
];

private _category = [_unit] call FUNC(symbologyUnitCategory);
[_category] call FUNC(symbologyDimension)
