#include "..\script_component.hpp"
/*
 * Type-guarded state read (issue #162 consolidation).
 *
 * The codebase reads missionNamespace state hundreds of times, each
 * with an inline `getVariable [key, default]` + `isEqualType` guard
 * against a nil/garbage value from a test edge case or an unset
 * producer.  That boilerplate repeats everywhere and is easy to skip -
 * a skipped guard is the #154 Pattern-1 bug class (a nil read falling
 * through to a `, 0` fallback that a code path treats as "gate off").
 *
 * This is the single guarded read.  The default comes from the caller,
 * and the _neverZero flag enforces the #154 rule: a GATE value that
 * defaults to 0 silently disables the system it gates.  Pass true when
 * the value is a gate (a 0 would wrongly turn something off), so a
 * missing state produces a SANE default instead of a silent kill.
 *
 * Arguments:
 *  0: key (STRING) - the missionNamespace variable, QGVAR-form
 *  1: default (ANY) - returned when missing or wrong type
 *  2: type (NUMBER 0..4, optional): 0 any, 1 number, 2 string,
 *     3 array, 4 bool.  Default 0 (any).
 *  3: neverZero (BOOL, optional, default false) - when true and the
 *     value is a number, a 0 result is replaced by the default
 *     (the #154 gate rule).
 *
 * Returns the stored value, or the default.
 */
params [["_key", "", [""]], ["_default", nil], ["_type", 0, [0]], ["_neverZero", false, [false]]];
if (_key == "") exitWith { _default };

private _val = missionNamespace getVariable [_key, _default];
private _ok = true;
if (_type == 1) then { _ok = _val isEqualType 0; };
if (_type == 2) then { _ok = _val isEqualType ""; };
if (_type == 3) then { _ok = _val isEqualType []; };
if (_type == 4) then { _ok = _val isEqualType true; };
if !(_ok) exitWith { _default };

if (_neverZero && {_val isEqualType 0} && {_val == 0}) exitWith { _default };
if (_neverZero && {_val isEqualType []} && {count _val == 0}) exitWith { _default };

_val
