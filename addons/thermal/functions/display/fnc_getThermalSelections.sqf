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
 * config is read once per class per session, not every refresh.
 *
 * Params:
 *   0: _object (OBJECT) - the unit/vehicle.
 *
 * Returns: ARRAY of selection INDICES.
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

// Vehicle: cache per class - the config does not change at runtime.
private _className = typeOf _object;
private _cacheKey = format ["%1_%2", QGVAR(thermalSelectionsCache), _className];
private _cached = missionNamespace getVariable [_cacheKey, []];
if (count _cached > 0) exitWith { _cached };

private _vehicleConfig = configFile >> "CfgVehicles" >> _className;
private _selectionNames = getArray (_vehicleConfig >> "hiddenSelections");
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
    } else {
        // 3. Fallback: all hiddenSelections except MFD/display screens.
        {
            if !(["mfd", _x, false] call BIS_fnc_inString) then {
                _selections pushBack _forEachIndex;
            };
        } forEach _selectionNames;
    };
    missionNamespace setVariable [_cacheKey, _selections];
    _selections
};
