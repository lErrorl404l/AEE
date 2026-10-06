#include "..\..\script_component.hpp"
/*
Runtime thermal capability probe (pure).

Returns whether an optic supports native thermal: a visionMode entry named
"Ti" (any case) AND a non-empty thermalMode array.  The kernel is
config-driven and pure: it reads no pixels and no engine vision mode, so the
unit suite can execute the real SQF with fixtures.

Params:
    0: _visionMode (ARRAY or CONFIG) - the optic's visionMode array, or the
       optic config's visionMode sub-config (the caller resolves
       `_optic >> "visionMode"`).  The kernel keeps the `>>` operator out of
       its own body so the pure harness can parse it.
    1: _thermalMode (ARRAY or CONFIG) - the thermalMode array, or the optic
       config's thermalMode sub-config.

Returns: BOOL - true when the optic supports native thermal.
*/
params [
    ["_visionMode", [], [[], configNull]],
    ["_thermalMode", [], [[], configNull]]
];

private _vm = _visionMode;
if !(_visionMode isEqualType []) then { _vm = getArray _visionMode; };
private _tm = _thermalMode;
if !(_thermalMode isEqualType []) then { _tm = getArray _thermalMode; };

// Case-insensitive membership: vanilla and workshop configs spell the mode
// "Ti" and "TI".  A for loop, not forEach: a block lambda is a pushed scope,
// so a scalar set inside it would not escape.
private _hasTi = false;
for "_i" from 0 to ((count _vm) - 1) do {
    private _mode = _vm select _i;
    if ((_mode isEqualTo "Ti") || (_mode isEqualTo "TI")) then { _hasTi = true; };
};

_hasTi && (_tm isNotEqualTo [])
