#include "..\..\script_component.hpp"
/*
 * aee_lib_fnc_evaluateGeoConsistency
 *
 * PURE evaluator for the positional consistency table.  It takes the table
 * and a value map and returns one verdict per row plus an overall
 * divergence flag.  It reads no world, no config, no missionNamespace and
 * no engine command: every input arrives in the value map, so the caller
 * owns all I/O and this function is testable in isolation.
 *
 * Arguments:
 *   0: table  <ARRAY> rows of [id, name, predicate, inputs, pairs,
 *              tolerance, severity, grade, note]
 *   1: values <ARRAY> a value map, [["key", value], ...]
 *
 * Predicates:
 *   "pairs_equal"  every declared pair is exactly equal (text or number)
 *   "agree_within" every declared pair is a numeric pair whose absolute
 *                  difference is at most the row tolerance
 *
 * A pair whose values are not both numeric fails "agree_within", so a
 * missing or mis-typed value is a divergence, never a silent pass.
 *
 * Return: [divergence <BOOL>, verdicts <ARRAY>]
 *   verdicts: [id <STRING>, pass <BOOL>, detail <STRING>, severity <STRING>]
 *   divergence is true when any row fails.  severity is carried through from
 *   the table so the monitor can grade the log line.
 *
 * The table is declared in data/consistency/position_invariants.json.  The
 * observability workstream owns addons/core/functions/fnc_evaluateConsistency
 * and data/consistency/invariants.json; this geo evaluator is self-contained
 * and uses a distinct table file, so a later merge of the two must reconcile
 * by adding the geo rows to that evaluator rather than keeping both.
 */
params [
    ["_table", [], [[]]],
    ["_values", [], [[]]]
];

// Key -> value lookup over the value map.  A for loop, not forEach: a
// forEach body does not persist an outer assignment in the test harness,
// and the explicit loop runs identically in the engine.
private _lookup = {
    params ["_map", "_key"];
    // An absent key yields the empty-array sentinel, which no predicate
    // treats as a valid numeric value, so a missing input diverges.
    private _found = [];
    for "_i" from 0 to ((count _map) - 1) do {
        private _pair = _map select _i;
        if ((_pair select 0) == _key) then { _found = _pair select 1; };
    };
    _found
};

private _verdicts = [];
private _divergence = false;

for "_r" from 0 to ((count _table) - 1) do {
    private _row = _table select _r;
    private _id = _row select 0;
    private _predicate = _row select 2;
    private _pairs = _row select 4;
    private _tolerance = _row select 5;
    private _severity = _row select 6;

    private _pass = true;
    private _detail = "";

    for "_p" from 0 to ((count _pairs) - 1) do {
        private _pair = _pairs select _p;
        private _keyA = _pair select 0;
        private _keyB = _pair select 1;
        private _valueA = [_values, _keyA] call _lookup;
        private _valueB = [_values, _keyB] call _lookup;
        private _ok = false;

        if (_predicate == "pairs_equal") then {
            _ok = (_valueA isEqualTo _valueB);
        } else {
            // agree_within: a numeric pair within the row tolerance.  A
            // non-numeric value leaves _ok false, which is a divergence.
            if ((_valueA isEqualType 0) && (_valueB isEqualType 0)) then {
                _ok = ((abs (_valueA - _valueB)) <= _tolerance);
            };
        };

        if (!_ok) then {
            _pass = false;
            _detail = _detail + _keyA + "=" + (str _valueA)
                + " " + _keyB + "=" + (str _valueB) + " ";
        };
    };

    if (!_pass) then { _divergence = true; };
    _verdicts pushBack [_id, _pass, _detail, _severity];
};

[_divergence, _verdicts]
