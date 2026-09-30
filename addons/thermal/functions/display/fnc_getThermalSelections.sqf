#include "..\..\script_component.hpp"
/*
 * Dynamic thermal-selection discovery (issue #204).
 *
 * The old code matched selection NAMES ("engine", "wheel", "tyre",
 * "camo") to decide what got heat - static, fragile, and wrong on any
 * modded or differently-named vehicle.  The proven thermal mods (MKK
 * 3753145363 fnc_getThermalSelections) discover the thermal
 * selections dynamically and NEVER match names:
 *
 *   - Man: every texture slot (uniforms have no hiddenSelections)
 *   - Vehicle: explicit config override first (MKK_TI >>
 *     mkk_ti_thermal_improvement_thermalSelections, then the legacy
 *     A3TI_ThermalSelections), then textureSources with non-empty
 *     textures, then ALL hiddenSelections except MFD/display screens.
 *
 * The result is cached per vehicle class (missionNamespace), so the
 * config is read once per class per session, not every refresh.  An EMPTY
 * result is cached too, guarded by a separate "computed" marker because
 * `count _cached > 0` cannot tell "not computed" from "computed empty".
 *
 * The names are read through fnc_getThermalSelectionNames, the single
 * source of truth every caller resolves the returned indices against.
 * That helper adds the runtime part-tree fallback (selectionNames) for a
 * model whose config omits hiddenSelections, so such an object becomes
 * solvable instead of returning [] and being dropped.
 *
 * Params:
 *   0: _object (OBJECT) - the unit/vehicle.
 *
 * Returns: ARRAY of selection INDICES into fnc_getThermalSelectionNames.
 */
params [["_object", objNull]];

if (isNull _object) exitWith { [] };

// Man: all texture slots.  Uniforms rarely declare hiddenSelections,
// so the texture slots are the only reliable source.
if (_object isKindOf "Man") exitWith {
    private _selections = [];
    for "_i" from 0 to ((count (getObjectTextures _object)) - 1) do {
        _selections pushBack _i;
    };
    _selections
};

// Vehicle: cache per class.  The authoritative name list is class-stable:
// config hiddenSelections when declared, else the model's own part tree,
// which every instance of a class shares.  A separate "computed" marker
// records that the class has been solved, because an EMPTY list is a
// legitimate result and `count _cached > 0` cannot tell it apart from
// "not computed yet" (which re-read the config every call for exactly the
// objects that yield nothing).
private _className = typeOf _object;
private _cacheKey = format ["%1_%2", QGVAR(thermalSelectionsCache), _className];
private _doneKey = format ["%1_%2", QGVAR(thermalSelectionsComputed), _className];
if (missionNamespace getVariable [_doneKey, false]) exitWith {
    missionNamespace getVariable [_cacheKey, []]
};

private _vehicleConfig = configFile >> "CfgVehicles" >> _className;
// Single source of truth for the index/name contract (issue #204): the
// SAME list the callers resolve the returned indices against.  It falls
// back to the runtime part tree for a model whose config omits
// hiddenSelections (scenery), which the sibling fnc_getSelectionMaterials
// already did - discovery did not, so those objects returned [] and were
// never painted.
private _selectionNames = [_object] call FUNC(getThermalSelectionNames);
private _custom = [];

// 1. Explicit override: MKK_TI then legacy A3TI_ThermalSelections.
private _profile = _vehicleConfig >> "MKK_TI";
if (isArray (_profile >> "mkk_ti_thermal_improvement_thermalSelections")) then {
    _custom = getArray (_profile >> "mkk_ti_thermal_improvement_thermalSelections");
} else {
    if (isArray (_vehicleConfig >> "A3TI_ThermalSelections")) then {
        _custom = getArray (_vehicleConfig >> "A3TI_ThermalSelections");
    };
};

if (_custom isNotEqualTo []) then {
    // The custom list may contain indices or names.
    private _converted = [];
    {
        private _index = if (_x isEqualType 0) then { _x } else { _selectionNames find _x };
        if (_index >= 0) then { _converted pushBackUnique _index; };
    } forEach _custom;
    missionNamespace setVariable [_cacheKey, _converted];
    missionNamespace setVariable [_doneKey, true];
    _converted
} else {
    // 2. textureSources: non-empty texture slots are paintable.
    private _selections = [];
    private _textureSources = [_vehicleConfig >> "textureSources"] call BIS_fnc_returnChildren;
    if (count _textureSources > 0) then {
        {
            private _textures = getArray (_x >> "textures");
            for "_i" from 0 to ((count _textures) - 1) do {
                if ((_textures select _i) != "") then {
                    _selections pushBackUnique _i;
                };
            };
        } forEach _textureSources;
        _selections = _selections select { _x < count _selectionNames };
    };
    // If textureSources produced nothing (empty textures, or none
    // declared), fall through to the all-but-MFD fallback - caching an
    // EMPTY list would leave the vehicle permanently unpainted (the
    // MRAP bug: heat ramped to 1 in the state but the parts never
    // rendered, issue #204).
    if (_selections isEqualTo []) then {
        // 3. Fallback: all hiddenSelections except MFD/display screens.
        {
            if !(["mfd", _x, false] call BIS_fnc_inString) then {
                _selections pushBack _forEachIndex;
            };
        } forEach _selectionNames;
    };
    missionNamespace setVariable [_cacheKey, _selections];
    missionNamespace setVariable [_doneKey, true];
    _selections
};
