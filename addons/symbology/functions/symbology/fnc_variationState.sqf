#include "..\..\script_component.hpp"
/*
 * aee_symbology_fnc_variationState
 *
 * Pure variation-state kernel.  Takes a list of [familyId, optionId, valueId]
 * triples and returns the normalised state for the family: one
 * [optionId, valueId] pair per option, in declaration order, with every option
 * present.  A missing or unknown value falls back to the family default, the
 * option's first value.  PURE: every input arrives as an argument and the
 * family table is loaded data, so the kernel reads no marker, no unit, no
 * setting and no world.
 *
 * Arguments:
 *   0: _pairs <ARRAY> [[familyId, optionId, valueId], ...]
 *
 * Return: <ARRAY> [[optionId, valueId], ...], or [] for an unknown family.
 */
params [
    ["_pairs", [], [[]]]
];

private _families = aee_symbology_variationFamilies;
private _family = [];
private _found = false;
if (_pairs isNotEqualTo []) then {
    private _familyId = (_pairs select 0) select 0;
    for "_i" from 0 to ((count _families) - 1) do {
        if (!_found && (_familyId isEqualTo ((_families select _i) select 0))) then {
            _family = _families select _i;
            _found = true;
        };
    };
};

private _state = [];
if (_found) then {
    private _options = _family select 5;
    {
        private _option = _x;
        private _optionId = _option select 0;
        private _values = _option select 3;
        private _valueId = "";
        {
            if ((_x select 1) isEqualTo _optionId) then {
                _valueId = _x select 2;
            };
        } forEach _pairs;
        // Validate against the option's values; a missing or unknown value
        // falls back to the first value, the family default.
        private _valid = false;
        for "_k" from 0 to ((count _values) - 1) do {
            if (((_values select _k) select 0) isEqualTo _valueId) then {
                _valid = true;
            };
        };
        if (!_valid) then {
            _valueId = "";
            if (_values isNotEqualTo []) then {
                _valueId = (_values select 0) select 0;
            };
        };
        _state pushBack [_optionId, _valueId];
    } forEach _options;
};

_state
