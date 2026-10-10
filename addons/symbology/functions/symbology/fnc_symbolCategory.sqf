#include "..\..\script_component.hpp"
/*
 * aee_optics_fnc_symbolCategory
 *
 * Pure category kernel.  Maps an engine marker type or a CfgVehicles class
 * token to a NATO APP-6(C) class category, using the generated table
 * aee_optics_symbologyTables.  PURE: the value and the kind arrive as
 * arguments and the table is loaded data, so the kernel reads no marker, no
 * unit and no world.
 *
 * Marker lookup order: the exact name, then the longest matching prefix, then
 * the suffix under that prefix, then the whole value as a suffix, then
 * "unknown".  The class lookup is one exact match on the class section.
 *
 * The loops are indexed, not forEach: the harness and SQF both keep an outer
 * scalar visible to an indexed for loop, which the resolver state needs.
 *
 * Arguments:
 *   0: _value <STRING> the marker type or the class token
 *   1: _kind  <STRING> "marker" (default) or "class"
 *
 * Return: <STRING> a class category.
 */
params [
    ["_value", "", [""]],
    ["_kind", "marker", [""]]
];

private _tables = aee_symbology_symbologyTables;
private _category = "";
private _found = false;

if (_kind isEqualTo "class") then {
    private _classes = _tables select 3;
    for "_i" from 0 to ((count _classes) - 1) do {
        if (!_found && (_value isEqualTo ((_classes select _i) select 0))) then {
            _category = (_classes select _i) select 1;
            _found = true;
        };
    };
} else {
    private _exact = _tables select 2;
    private _prefixes = _tables select 0;
    private _suffixes = _tables select 1;

    for "_i" from 0 to ((count _exact) - 1) do {
        if (!_found && (_value isEqualTo ((_exact select _i) select 0))) then {
            _category = (_exact select _i) select 1;
            _found = true;
        };
    };

    private _prefix = "";
    private _fallback = "";
    private _candidate = "";
    for "_i" from 0 to ((count _prefixes) - 1) do {
        _candidate = (_prefixes select _i) select 0;
        if (!_found
            && ((_value select [0, count _candidate]) isEqualTo _candidate)
            && ((count _candidate) > (count _prefix))) then {
            _prefix = _candidate;
            _fallback = (_prefixes select _i) select 1;
        };
    };

    if (_prefix isNotEqualTo "") then {
        private _rest = _value select [count _prefix];
        for "_i" from 0 to ((count _suffixes) - 1) do {
            if (!_found && (_rest isEqualTo ((_suffixes select _i) select 0))) then {
                _category = (_suffixes select _i) select 1;
                _found = true;
            };
        };
        if (!_found) then {
            _category = _fallback;
            _found = true;
        };
    };

    if (!_found) then {
        for "_i" from 0 to ((count _suffixes) - 1) do {
            if (!_found && (_value isEqualTo ((_suffixes select _i) select 0))) then {
                _category = (_suffixes select _i) select 1;
                _found = true;
            };
        };
    };
};

if (!_found) then { _category = "unknown"; };

_category
