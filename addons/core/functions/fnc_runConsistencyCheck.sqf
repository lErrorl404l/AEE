#include "..\script_component.hpp"

/*
Throttled runtime consistency monitor (cross-module).

The monitor reads the published producer variables into a value map, reads the
declarative invariant table (FUNC(consistencyLoadTable)), and asks the pure
evaluator (FUNC(evaluateConsistency)) whether the modules agree.  It then
publishes the verdict and one human line per failing invariant.

Read-only by construction.  Every producer value is read with
`missionNamespace getVariable [name, default]`.  The monitor writes only its
own core state and it never calls `publicVariable`, so no other module's state
is touched and there is no load-order dependency.  A producer that is unset
resolves to the no-data sentinel, the evaluator marks the row no-data, and the
row is never a failure: the monitor never throws on missing state.

The first line of a run carries the module-health report (task 4) folded in,
so one line names both the invariant result and any module that did not
initialise.

The caller (addons/core/XEH_postInit.sqf) throttles the call; this function
does the work for one sample.

Publishes:
  aee_core_consistencyState     [overallPass, verdicts, modulesInDisagreement]
  aee_core_consistencyFailures  one failure message per failing invariant

Arguments: none.

Returns: Nothing.
Public: No
Example: [] call aee_core_fnc_runConsistencyCheck
*/

private _table = [] call FUNC(consistencyLoadTable);

// ── Value map from the published producers ─────────────────────────────────
// Only scalars (NUMBER or BOOL) enter the map.  A missing producer resolves to
// the no-data string, and a container (for example the per-cell
// aee_thermal_groundNodeStack HashMap) is dropped, so the evaluator never
// compares a non-scalar and the monitor never throws.
private _values = [];
{
    private _producers = _x select 2;
    {
        private _v = missionNamespace getVariable [_x select 1, "__aee_no_data__"];
        if (_v isEqualTypeAny [0, true]) then {
            _values pushBack [(_x select 1), _v];
        };
    } forEach _producers;
} forEach _table;

// ── Evaluate ───────────────────────────────────────────────────────────────
private _result = [_table, _values] call FUNC(evaluateConsistency);
private _pass = _result select 0;
private _rows = _result select 1;

private _strict = missionNamespace getVariable ["aee_core_consistencyStrict", false];
if !(_strict isEqualType false) then { _strict = false; };

// ── Module health (task 4), folded into the first line ─────────────────────
private _health = missionNamespace getVariable ["aee_core_moduleHealth", []];
private _unhealthy = [];
{
    if (!(_x select 1) || {!(_x select 2)}) then { _unhealthy pushBack (_x select 0); };
} forEach _health;
private _healthSuffix = " | health all-up";
if (_unhealthy isNotEqualTo []) then {
    _healthSuffix = " | health";
    for "_i" from 0 to ((count _unhealthy) - 1) do {
        _healthSuffix = _healthSuffix + " " + (_unhealthy select _i);
    };
};

// ── One line per failing row ───────────────────────────────────────────────
private _failures = [];
private _disagreeTotal = 0;
private _firstLine = true;
for "_r" from 0 to ((count _rows) - 1) do {
    private _verdict = _rows select _r;
    private _rowPass = _verdict select 1;
    private _detail = _verdict select 2;
    private _count = _verdict select 3;
    private _tolerance = (_table select _r) select 4;
    private _report = [_table select _r, _values, _verdict] call FUNC(consistencyFailureLine);
    private _drift = _report select 1;
    // Strict mode reports a residual: a row that PASSED with a drift inside
    // its tolerance and a full comparison.  The failure-line drift is the
    // spread of every present producer, so it is only a "residual" when the
    // predicate compared those producers.  A no-data row (a missing producer)
    // made no comparison, and an out-of-scope row (INV-1 in daylight) left the
    // tolerance, so neither is a residual.  Gating on the tolerance is the
    // difference between a diagnostic and the WARN flood the operator reported:
    // without it strict logged every passing row every sample.
    private _strictResidual = _strict && {_drift > 0} && {_drift <= _tolerance} && {_detail != "no-data"};
    if ((!_rowPass) || {_strictResidual}) then {
        private _line = _report select 0;
        if (_firstLine) then {
            _line = _line + _healthSuffix;
            _firstLine = false;
        };
        if (!_rowPass) then {
            // A failing invariant is a warning.
            _disagreeTotal = _disagreeTotal + _count;
            _failures pushBack _line;
            [_line] call FUNC(consistencyLog);
        } else {
            // A passing invariant is informational, never a warning.
            [_line, "INFO"] call FUNC(consistencyLog);
        };
    };
};

// A healthy first run still emits one line, so the module health is always
// reported once by the monitor.
private _prev = missionNamespace getVariable ["aee_core_consistencyState", []];
if (((count _prev) == 0) && _firstLine) then {
    private _summary = "consistency: pass=" + (str _pass) + " rows=" + (str (count _rows)) + _healthSuffix;
    [_summary, "INFO"] call FUNC(consistencyLog);
};

missionNamespace setVariable ["aee_core_consistencyState", [_pass, _rows, _disagreeTotal]];
missionNamespace setVariable ["aee_core_consistencyFailures", _failures];
