#include "..\script_component.hpp"

/*
aee_diagnostics_fnc_test

Runs the in-engine unit tests for one AEE component (addon).

Mirrors CBA_fnc_test, which execs "\x\<addon>\addons\<component>\test.sqf".
AEE mounts at \z\aee\addons\<component>, so the runner uses AEE's own root.
The file is compiled with preprocessFileLineNumbers and called, not execVM'd:
the runtime preprocessor does not resolve the addon file's #include under
execVM, so its handle is unusable.  The test reads the live merged config and
renders nothing, so a dedicated server runs it.

The component test.sqf publishes its failure count to
aee_test_failures_<component> before it ends, so this runner returns a NUMBER.
A missing file returns -1 and logs a warning rather than failing silently.

The message is built into a variable before it reaches AEE_LOG_*: HEMTT splits
a macro argument on every comma, so a format [..] with arguments cannot be
passed inline.

Arguments:
    0: _component <STRING> component (addon) name; "main" is the whole addon.

Return Value:
    <NUMBER> the component's failure count: 0 = every assertion passed,
             > 0 = that many failed, -1 = the component ships no test.sqf.
Public: Yes, also exposed as AEE_fnc_test (XEH_postInit.sqf).
Example: ["cartography"] call aee_diagnostics_fnc_test
*/

params [["_component", "main", [""]]];

private _path = format ["\z\aee\addons\%1\test.sqf", _component];
if !(fileExists _path) exitWith {
    private _missing = format ["no test.sqf for component '%1'", _component];
    AEE_LOG_WARN(_missing);
    -1
};

private _start = format ["running tests: %1", _path];
AEE_LOG_INFO(_start);

// The component test reads the live merged config and pure kernels only, so it
// runs to completion synchronously: compile-and-call runs it in this thread.
// A script handle is NOT used.  execVM returns the path STRING for these addon
// files (the runtime preprocessor does not resolve their #include), so
// scriptDone on that value never fires and the runner would hang.
// preprocessFileLineNumbers resolves the include exactly as CBA's PREP does for
// every AEE function, so the macros the test files use are defined.
private _code = compile preprocessFileLineNumbers _path;
if (isNil "_code") exitWith {
    private _bad = format ["test.sqf for '%1' did not compile", _component];
    AEE_LOG_ERROR(_bad);
    -1
};
call _code;

private _failures = missionNamespace getVariable [format ["aee_test_failures_%1", _component], -1];
private _end = format ["tests complete: %1 (%2 failed)", _component, _failures];
AEE_LOG_INFO(_end);

_failures
