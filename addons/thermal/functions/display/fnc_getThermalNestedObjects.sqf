#include "..\..\script_component.hpp"
/*
 * Thermal nested objects (issue #204, option a of the recursive walk).
 *
 * fnc_expandThermalSelectionTree records every separately attached object
 * and cargo vehicle it reaches.  A parent selection index cannot express a
 * part on another object, because setObjectTexture writes only the target
 * object's own texture slots.  This function returns those objects so a
 * caller can invoke fnc_getThermalSelections on each of them separately.
 *
 * The list is populated by the walk; the caller may read it after a
 * discovery call on the parent.  An object with no recorded children returns
 * an empty array, never nil.
 *
 * Params:
 *   0: _object (OBJECT) - the parent object.
 *
 * Returns: ARRAY of OBJECT - the separate nested objects, or [].
 */
params [["_object", objNull, [objNull]]];

if (isNull _object) exitWith { [] };

private _store = missionNamespace getVariable [QGVAR(thermalNestedObjects), -1];
if (_store isEqualType 0) exitWith { [] };

_store getOrDefault [str _object, []]
