#include "..\..\script_component.hpp"
/*
 * aee_optics_fnc_symbologyMarkerCategory
 *
 * Engine adapter.  Reads an engine marker's type and maps it to a class
 * category through the pure kernel FUNC(symbolCategory).  The type override
 * is a test seam: an empty override makes the adapter read markerType.
 *
 * Arguments:
 *   0: _marker       <STRING> the marker name
 *   1: _typeOverride <STRING> optional marker type, for a headless call
 *
 * Return: <STRING> a class category.
 */
params [
    ["_marker", "", [""]],
    ["_typeOverride", "", [""]]
];

private _type = _typeOverride;
if (_type isEqualTo "") then {
    _type = markerType _marker;
};

[_type, "marker"] call FUNC(symbolCategory)
