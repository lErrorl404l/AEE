// PHASE 138: the native thermal kernel parity.
//
// The two-node solve is a pure kernel and server-callable, so this probe drives
// it directly on the dedicated server: it computes the SQF reference answer and
// calls the native extension command with the same 25 arguments, then compares
// each element within the per-kernel bound justified in ADR-034.  It renders
// nothing.
//
// When the extension is loaded the native command answers and the probe marks
// the native path.  When it is absent the native call returns no payload: the
// probe records native-unavailable and asserts the dispatcher returns the SQF
// fallback, and it never claims the native path passed.

private _dispatch = missionNamespace getVariable ["aee_core_fnc_dispatchKernel", nil];

// [native command, SQF reference function, 25 kernel args, relative bound]
private _cases = [
    ["kernel.solveTwoNodeKernel", "aee_thermal_fnc_solveTwoNodeKernel",
        [15, 1, 500, 1, 63, 7, 1.8258, 0.15, 36.8, 33.7, 120,
         "vertical", 0.5, 15, true, true, 5, 0, -273, 0, 1, 0,
         1, 0.95, 0.7], 1e-3],
    ["kernel.solveTwoNodeKernel", "aee_thermal_fnc_solveTwoNodeKernel",
        [0, 5, 0, 1, 63, 7, 1.8258, 0.15, 35, 28, 80,
         "vertical", 0.5, 0, true, true, 5, 0, -273, 0, 1, 0,
         1, 0.95, 0.7], 1e-3],
    ["kernel.solveTwoNodeKernel", "aee_thermal_fnc_solveTwoNodeKernel",
        [0, 5, 0, 1, 50, 20, 6, 1.5, 0, 0, 5000,
         "vertical", 0.5, 0, false, false, 5, 0, -273, 0, 1, 0,
         1, 0.9, 0.5], 1e-3]
];

private _pass = 0;
private _fail = 0;
private _nativeChecked = 0;
private _nativeUnavailable = 0;
private _notes = [];

{
    _x params ["_nativeName", "_refName", "_args", "_rel"];
    private _refFn = missionNamespace getVariable [_refName, nil];
    if (isNil "_refFn") then {
        _fail = _fail + 1;
        _notes pushBack format ["reference %1 not compiled", _refName];
        continue;
    };
    private _expected = _args call _refFn;
    if !(_expected isEqualType []) then { _expected = [_expected]; };

    // arma-rs answers `callExtension [cmd, args]` with [output, errorCode,
    // aux]; an absent extension answers with "".  A successful call needs a
    // non-empty output and errorCode 0.
    private _nativeOut = "aee_dev" callExtension [_nativeName, _args];
    private _payload = "";
    private _code = 0;
    if (_nativeOut isEqualType []) then {
        _payload = _nativeOut param [0, ""];
        _code = _nativeOut param [1, -1];
    } else {
        if (_nativeOut isEqualType "") then { _payload = _nativeOut; };
    };

    private _actual = [];
    private _source = "";
    if ((_payload isEqualType "") && {_payload != ""} && {_code isEqualType 0} && {_code == 0}) then {
        _nativeChecked = _nativeChecked + 1;
        _actual = parseSimpleArray _payload;
        _source = "native";
    } else {
        _nativeUnavailable = _nativeUnavailable + 1;
        if (!isNil "_dispatch") then {
            private _dispatched = ["solveTwoNodeKernel", _args] call _dispatch;
            if (_dispatched isEqualType "") then { _dispatched = parseSimpleArray _dispatched; };
            if (_dispatched isEqualType []) then { _actual = _dispatched; _source = "fallback"; };
        };
    };

    if ((count _actual) != (count _expected)) then {
        _fail = _fail + 1;
        _notes pushBack format ["%1 %2: expected %3 elements, got %4", _refName, _source, count _expected, count _actual];
    } else {
        private _caseOk = true;
        {
            private _want = _x;
            private _got = _actual select _forEachIndex;
            private _bound = _rel * (abs _want);
            if (!(abs (_want - _got) <= _bound)) then {
                _caseOk = false;
                _notes pushBack format ["%1 %2[%3]: expected %4 got %5 (bound %6)", _refName, _source, _forEachIndex, _want, _got, _bound];
            };
        } forEach _expected;
        if (_caseOk) then { _pass = _pass + 1; } else { _fail = _fail + 1; };
    };
} forEach _cases;

private _marker = if (_nativeChecked > 0) then { "native" } else { "native-unavailable" };
diag_log text format ["[P138] thermal kernel path marker %1 (native %2, unavailable %3)", _marker, _nativeChecked, _nativeUnavailable];

if (_fail isEqualTo 0) then {
    diag_log text format ["[P138] [PASS] thermal kernel parity: %1 checks, %2", _pass, _marker];
} else {
    diag_log text format ["[P138] [FAIL] thermal kernel parity: %1 passed, %2 failed: %3", _pass, _fail, str _notes];
};
