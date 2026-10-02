#include "..\..\script_component.hpp"
/*
 * Thermal selection tree walk (issue #204, operator recursive-tree directive).
 *
 * fnc_getThermalSelections resolves the object's LEVEL 0 selections.  This
 * function is the walk that continues "until there is no more to find": it
 * adds same-object breadth and it visits the separate objects in the tree.
 *
 * Walk order:
 *   1. the object's addressable name list (selectionNames, default LOD) and
 *      the names the level-0 result already covers;
 *   2. every named LOD (selectionNames "<LOD>") - memory points, collision
 *      parts, hit points, view geometry;
 *   3. every turret config (allTurrets -> BIS_fnc_turretConfig) and its
 *      hiddenSelections declaration;
 *   4. attachedObjects and getVehicleCargo - each a SEPARATE object, recursed
 *      into and recorded for the caller.
 * A candidate is added only when its name is addressable on THIS object (it
 * appears in the default-LOD selection list) and it is not already covered,
 * so the index is a real paint target and the level-0 order is not disturbed.
 *
 * BOUNDS (named constants, the walk provably terminates):
 *   _MAX_DEPTH   nested-object recursion levels below the root;
 *   _MAX_OBJECTS objects visited per walk (the visited-set cap);
 *   _MAX_TARGETS selections returned per call (a wide-tree cap).
 * A visited set keyed by str object stops a cycle or a self-reference.  The
 * per-class cache in fnc_getThermalSelections stops a re-walk per tick.
 *
 * CEILING (honest, do not attempt): a proxy appears only as a placement NAME
 * in the parent's selectionNames ("proxy:\a3\...\weapon.001"):
 * no script handle exists for a proxy, so its INTERNAL selections are
 * unreachable.  A name matching "proxy:" is skipped and is never returned as
 * a paint target.  The model.cfg / CfgModels tree is consumed at
 * binarization, not script-readable.
 *
 * Params:
 *   0: _object    (OBJECT) - the node to walk.
 *   1: _selections (ARRAY) - the level-0 indices on THIS object.
 *   2: _depth     (NUMBER) - recursion depth, 0 at the root.
 *   3: _visited   (ARRAY)  - str ids already walked (passed by reference).
 *
 * Returns: ARRAY of selection INDICES on _object (level-0 plus level-1).
 *   Separate nested objects are recorded under QGVAR(thermalNestedObjects).
 */
params [
    ["_object", objNull, [objNull]],
    ["_selections", [], [[]]],
    ["_depth", 0, [0]],
    ["_visited", [], [[]]]
];

if (isNull _object) exitWith { _selections };

// Named bounds.  Changing a cap is the one place the walk's reach changes.
private _MAX_DEPTH = 3;
private _MAX_OBJECTS = 32;
private _MAX_TARGETS = 256;
private _LODS = ["Memory", "Geometry", "FireGeometry", "LandContact", "HitPoints", "ViewGeometry"];

_visited pushBackUnique (str _object);

// The object's addressable names: the default-LOD selection list, exactly the
// list fnc_getThermalSelectionNames and fnc_applySelectionThermal resolve
// against.  No names means nothing this walk can paint.
private _names = selectionNames _object;
if (_names isEqualTo []) exitWith { _selections };

// Names the level-0 result already covers, so the walk only ADDS breadth.
private _covered = [];
{
    if ((_x isEqualType 0) && (_x >= 0) && (_x < count _names)) then {
        _covered pushBack (_names select _x);
    };
} forEach _selections;

// ── Level 1: same-object breadth ────────────────────────────────────────────
private _candidates = [];
{
    private _lod = _x;
    {
        _candidates pushBack _x;
    } forEach (_object selectionNames _lod);
} forEach _LODS;

{
    // BIS_fnc_turretConfig returns configNull for a bad path, and getArray on
    // configNull is empty, so no separate null check is needed.
    private _turretCfg = [_object, _x] call BIS_fnc_turretConfig;
    if (isArray (_turretCfg >> "hiddenSelections")) then {
        {
            _candidates pushBack _x;
        } forEach (getArray (_turretCfg >> "hiddenSelections"));
    };
} forEach (allTurrets _object);

{
    private _name = _x;
    // A proxy name is a placement marker, not a texture target: skip it.
    if ((_name isEqualType "") && ((_name find "proxy:") != 0)) then {
        private _idx = _names find _name;
        if ((_idx >= 0) && (!(_name in _covered)) && ((count _selections) < _MAX_TARGETS)) then {
            _selections pushBackUnique _idx;
            _covered pushBack _name;
        };
    };
} forEach _candidates;

// ── Level 2: separate nested objects (option a) ─────────────────────────────
// attachedObjects / getVehicleCargo return SEPARATE objects.  A parent index
// cannot address them, because setObjectTexture writes only the target
// object's own slots.  The walk recurses to discover their trees and records
// each object, so a caller can invoke fnc_getThermalSelections on it
// (fnc_getThermalNestedObjects).  The recursion is bounded by the depth cap,
// the visited set and the object cap, so a cycle or a self-reference stops.
if ((_depth < _MAX_DEPTH) && ((count _visited) < _MAX_OBJECTS)) then {
    private _nested = (attachedObjects _object) + (getVehicleCargo _object);
    if (_nested isNotEqualTo []) then {
        private _store = missionNamespace getVariable [QGVAR(thermalNestedObjects), -1];
        if (_store isEqualType 0) then {
            _store = createHashMap;
            missionNamespace setVariable [QGVAR(thermalNestedObjects), _store];
        };
        private _recorded = _store getOrDefault [str _object, []];
        {
            private _child = _x;
            if ((!isNull _child) && (!((str _child) in _visited))) then {
                _visited pushBack (str _child);
                _recorded pushBack _child;
                [_child, [], _depth + 1, _visited] call FUNC(expandThermalSelectionTree);
            };
        } forEach _nested;
        _store set [str _object, _recorded];
    };
};

_selections
