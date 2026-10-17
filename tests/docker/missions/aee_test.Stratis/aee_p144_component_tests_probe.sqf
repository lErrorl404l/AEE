// PHASE 144: the per-component in-engine test suite, run through the AEE
// runner (aee_diagnostics_fnc_test), which mirrors CBA_fnc_test but uses
// AEE's own mount root: it execs \z\aee\addons\<component>\test.sqf and
// returns that component's failure count.
//
// This probe drives the five visual-surface components and emits one [P144]
// PASS/FAIL line.  It renders nothing: every component test is headless-safe
// (the live merged config and pure kernels only), so the dedicated server
// carries it.

private _components = ["cartography", "symbology", "thermal_display", "nightvision", "lighting"];
private _fnTest = missionNamespace getVariable ["aee_diagnostics_fnc_test", nil];
if (isNil "_fnTest") exitWith {
    diag_log text "[P144] [FAIL] component test runner not compiled (aee_diagnostics_fnc_test)";
};

private _fail = 0;
private _notes = [];
{
    // The runner returns the component's failure count: 0 = every assertion
    // passed, > 0 = that many failed, -1 = the component ships no test.sqf.
    private _n = [_x] call _fnTest;
    if (!(_n isEqualType 0) || {_n < 0}) then {
        _fail = _fail + 1;
        _notes pushBack format ["%1: runner returned %2", _x, _n];
    } else {
        if (_n > 0) then {
            _fail = _fail + 1;
            _notes pushBack format ["%1: %2 failed", _x, _n];
        };
    };
} forEach _components;

if (_fail == 0) then {
    diag_log text format ["[P144] [PASS] component tests (%1 components)", count _components];
} else {
    diag_log text format ["[P144] [FAIL] component tests: %1 component(s): %2", _fail, str _notes];
};
