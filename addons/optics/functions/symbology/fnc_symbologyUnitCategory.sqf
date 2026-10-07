#include "..\..\script_component.hpp"
/*
 * aee_optics_fnc_symbologyUnitCategory
 *
 * Engine adapter.  Reads a unit's CfgVehicles vehicleClass and unitClass and
 * maps them to a class category through the pure kernel FUNC(symbolCategory).
 * The vehicleClass is tried first; the unitClass is the fallback.
 *
 * Arguments:
 *   0: _unit <STRING> the unit (an object in the engine)
 *
 * Return: <STRING> a class category.
 */
params [
    ["_unit", "", [""]]
];

private _class = typeOf _unit;
private _config = configFile >> "CfgVehicles" >> _class;

private _category = [getText (_config >> "vehicleClass"), "class"] call FUNC(symbolCategory);
if (_category isEqualTo "unknown") then {
    _category = [getText (_config >> "unitClass"), "class"] call FUNC(symbolCategory);
};

_category
