#include "..\..\script_component.hpp"
/*
 * Thermal nested objects (issue #204, option a of the recursive walk).
 *
 * attachedObjects and getVehicleCargo return SEPARATE objects: an attached
 * weapon holder, a cargo vehicle.  A parent selection index cannot express a
 * part on another object, because setObjectTexture writes only the target
 * object's own slots.  This function returns an object's DIRECT nested objects
 * so the caller can invoke fnc_getThermalSelections on each of them as its own
 * object.
 *
 * The discovery is PER INSTANCE: attachedObjects and getVehicleCargo are
 * runtime state, so they cannot live in the class-cached selection list
 * (fnc_expandThermalSelectionTree).  The first call for an object walks and
 * records; every later call is a hashmap lookup, never a re-walk.
 *
 * BOUNDS (named constants, the discovery provably terminates):
 *   _MAX_DEPTH   nested-object recursion levels below this object;
 *   _MAX_OBJECTS objects visited per discovery (the visited-set cap).
 * A visited set keyed by str object stops a cycle or a self-reference.
 *
 * CEILING (honest, do not attempt): a proxy's internal selections are not
 * scriptable; model.cfg is consumed at binarization.  This records separate
 * objects, not proxy internals.
 *
 * Params:
 *   0: _object  (OBJECT) - the parent object.
 *   1: _depth   (NUMBER) - recursion depth, internal.
 *   2: _visited (ARRAY)  - str ids already walked (passed by reference).
 *
 * Returns: ARRAY of OBJECT - the direct nested objects, or [].
 */
params [
    ["_object", objNull, [objNull]],
    ["_depth", 0, [0]],
    ["_visited", [], [[]]]
];

if (isNull _object) exitWith { [] };

private _MAX_DEPTH = 3;
private _MAX_OBJECTS = 32;
private _MAX_STORE = 4096;

private _store = missionNamespace getVariable [QGVAR(thermalNestedObjects), -1];
if (_store isEqualType 0) then {
    _store = createHashMap;
    missionNamespace setVariable [QGVAR(thermalNestedObjects), _store];
};

// The store is keyed by object instance, so a long session with respawning
// objects would grow it without limit.  Clear it at the cap; a cleared entry
// is discovered again on the next call.
if ((count _store) > _MAX_STORE) then {
    _store = createHashMap;
    missionNamespace setVariable [QGVAR(thermalNestedObjects), _store];
};

private _key = str _object;

// Already discovered for this instance: return the recorded list, do not walk.
private _recorded = _store getOrDefault [_key, -1];
if (_recorded isEqualType []) exitWith { _recorded };

_visited pushBackUnique _key;
_recorded = [];

if ((_depth < _MAX_DEPTH) && ((count _visited) < _MAX_OBJECTS)) then {
    private _nested = (attachedObjects _object) + (getVehicleCargo _object);
    {
        private _child = _x;
        if ((!isNull _child) && {!((str _child) in _visited)}) then {
            _visited pushBack (str _child);
            _recorded pushBack _child;
            [_child, _depth + 1, _visited] call FUNC(getThermalNestedObjects);
        };
    } forEach _nested;
};

_store set [_key, _recorded];

_recorded
