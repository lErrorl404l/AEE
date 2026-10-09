// PHASE 139: the native drag and eye kernel parity.
//
// The drag and eye kernels are PURE kernels and server-callable.  Their real
// call sites are client-local (the drag `Fired` handler and the `hasInterface`
// eye driver), and those integrations are manual `interface` ceilings recorded
// in ADR-033.  A pure kernel needs no player, so this probe drives each kernel
// DIRECTLY on the dedicated server: it computes the SQF reference answer and
// calls the native extension command with the same arguments, then compares
// within the per-kernel bound justified in ADR-034.  It renders nothing.
//
// When the extension is loaded the native command answers and the probe marks
// the native path.  When it is absent the native call returns no payload: the
// probe records native-unavailable and asserts the dispatcher returns the SQF
// fallback, and it never claims the native path passed.

private _dispatch = missionNamespace getVariable ["aee_core_fnc_dispatchKernel", nil];

// [kernel id, native command, SQF reference function, args, relative bound, absolute bound]
private _cases = [
    ["calculateBallisticDrag", "kernel.calculateBallisticDrag", "aee_ballistics_fnc_calculateBallisticDrag", [0.307, 900, "G1", 1.0, 15], 1e-6, 0],
    ["calculateBallisticDrag", "kernel.calculateBallisticDrag", "aee_ballistics_fnc_calculateBallisticDrag", [1.05, 850, "G7", 0.8, -20], 1e-6, 0],
    ["calculateBallisticDrag", "kernel.calculateBallisticDrag", "aee_ballistics_fnc_calculateBallisticDrag", [0.4, 1200, "LW2", 1.0, 25], 1e-6, 0],
    ["eyeAdaptStep", "kernel.eyeAdaptStep", "aee_optics_fnc_eyeAdaptStep", [[0, 0], 1, 0.1, 2, 120, 400, 0], 1e-6, 0],
    ["eyeAdaptStep", "kernel.eyeAdaptStep", "aee_optics_fnc_eyeAdaptStep", [[-3, -3], -1, 1, 2, 120, 400, 0], 1e-6, 0],
    ["eyeMesopicWeight", "kernel.eyeMesopicWeight", "aee_optics_fnc_eyeMesopicWeight", [0.1, 0.005, 5], 1e-6, 0],
    ["eyeMesopicWeight", "kernel.eyeMesopicWeight", "aee_optics_fnc_eyeMesopicWeight", [100, 0.005, 5], 1e-6, 0],
    ["eyePupilSteady", "kernel.eyePupilSteady", "aee_optics_fnc_eyePupilSteady", [1], 1e-6, 0],
    ["eyePupilSteady", "kernel.eyePupilSteady", "aee_optics_fnc_eyePupilSteady", [1000], 1e-6, 0],
    ["eyePupilStep", "kernel.eyePupilStep", "aee_optics_fnc_eyePupilStep", [2, 8, 0.1, 0.25, 0.475], 1e-6, 0],
    ["eyePupilStep", "kernel.eyePupilStep", "aee_optics_fnc_eyePupilStep", [8, 2, 0.1, 0.25, 0.475], 1e-6, 0],
    ["eyeTimeSkip", "kernel.eyeTimeSkip", "aee_optics_fnc_eyeTimeSkip", [-1, 5, 0.05], 1e-6, 0],
    ["eyeTimeSkip", "kernel.eyeTimeSkip", "aee_optics_fnc_eyeTimeSkip", [23, 1, 0.05], 1e-6, 0]
];

private _pass = 0;
private _fail = 0;
private _nativeChecked = 0;
private _nativeUnavailable = 0;
private _notes = [];

{
    _x params ["_id", "_nativeName", "_refName", "_args", "_rel", "_abs"];
    private _refFn = missionNamespace getVariable [_refName, nil];
    if (isNil "_refFn") then {
        _fail = _fail + 1;
        _notes pushBack format ["%1: reference %2 not compiled", _id, _refName];
        continue;
    };
    private _expected = _args call _refFn;

    // arma-rs answers `callExtension [cmd, args]` with [output, errorCode,
    // aux]; an absent extension answers with "".  A successful native call
    // needs a non-empty output and errorCode 0.
    private _nativeOut = "aee_dev" callExtension [_nativeName, _args];
    private _payload = "";
    private _code = 0;
    if (_nativeOut isEqualType []) then {
        _payload = _nativeOut param [0, ""];
        _code = _nativeOut param [1, -1];
    } else {
        if (_nativeOut isEqualType "") then { _payload = _nativeOut; };
    };

    // A non-nil sentinel: when neither the native path nor the fallback yields
    // a result, `_actual` fails every type check below instead of being read as
    // an engine nil (which is toxic to isEqualType).
    private _actual = [];
    private _source = "";
    if ((_payload isEqualType "") && {_payload != ""} && {_code isEqualType 0} && {_code == 0}) then {
        _nativeChecked = _nativeChecked + 1;
        _actual = _payload;
        _source = "native";
    } else {
        _nativeUnavailable = _nativeUnavailable + 1;
        _source = "fallback";
        if (!isNil "_dispatch") then {
            _actual = [_id, _args] call _dispatch;
        };
    };

    private _caseOk = false;
    if (_expected isEqualType []) then {
        if (_actual isEqualType "") then { _actual = parseSimpleArray _actual; };
        if ((_actual isEqualType []) && {(count _actual) == (count _expected)}) then {
            _caseOk = true;
            {
                private _want = _x;
                private _got = _actual select _forEachIndex;
                private _itemBound = _abs + (_rel * abs _want);
                if (!(abs (_want - _got) <= _itemBound)) then {
                    _caseOk = false;
                    _notes pushBack format ["%1 %2[%3]: expected %4 got %5 (bound %6)", _id, _source, _forEachIndex, _want, _got, _itemBound];
                };
            } forEach _expected;
        } else {
            _notes pushBack format ["%1 %2: expected %3 elements, got %4", _id, _source, count _expected, count _actual];
        };
    } else {
        if (_expected isEqualType true) then {
            if (_actual isEqualType "") then { _actual = (_actual == "true"); };
            _caseOk = (_actual isEqualType true) && {_actual == _expected};
        } else {
            if (_actual isEqualType "") then { _actual = parseNumber _actual; };
            private _bound = _abs + (_rel * abs _expected);
            _caseOk = (_actual isEqualType 0) && {(abs (_expected - _actual)) <= _bound};
            if (!_caseOk) then {
                _notes pushBack format ["%1 %2: expected %3 got %4 (bound %5)", _id, _source, _expected, _actual, _bound];
            };
        };
        if ((_expected isEqualType true) && {!_caseOk}) then {
            _notes pushBack format ["%1 %2: expected %3 got %4", _id, _source, _expected, _actual];
        };
    };
    if (_caseOk) then { _pass = _pass + 1; } else { _fail = _fail + 1; };
} forEach _cases;

private _marker = if (_nativeChecked > 0) then { "native" } else { "native-unavailable" };
diag_log text format ["[P139] client kernel path marker %1 (native %2, unavailable %3)", _marker, _nativeChecked, _nativeUnavailable];

if (_fail isEqualTo 0) then {
    diag_log text format ["[P139] [PASS] drag and eye kernel parity: %1 checks, %2", _pass, _marker];
} else {
    diag_log text format ["[P139] [FAIL] drag and eye kernel parity: %1 passed, %2 failed: %3", _pass, _fail, str _notes];
};
