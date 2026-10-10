// PHASE 137: the native kernel parity.
//
// The pure kernels are server-callable, so this probe drives each one directly
// on the dedicated server: it computes the SQF reference answer and calls the
// native extension command with the same arguments, then compares the two
// within the per-kernel bound justified in ADR-036.  It renders nothing.
//
// When the extension is loaded the native command answers and the probe marks
// the native path.  When it is absent the native call returns an empty string:
// the probe then records native-unavailable and asserts that the dispatcher
// returns the SQF fallback, and it never claims the native path passed.

private _dispatch = missionNamespace getVariable ["aee_core_fnc_dispatchKernel", nil];

// [kernel id, native command, SQF reference function, args, relative bound, absolute bound]
private _cases = [
    ["calculateStationPressure", "kernel.calculateStationPressure", "aee_atmos_fnc_calculateStationPressure", [1013.25, 1000, 6.5], 1e-6, 0],
    ["calculateStationPressure", "kernel.calculateStationPressure", "aee_atmos_fnc_calculateStationPressure", [900, 5000, 8.0], 1e-6, 0],
    ["calculateStationPressure", "kernel.calculateStationPressure", "aee_atmos_fnc_calculateStationPressure", [1013.25, 20000, 6.5], 1e-6, 0],
    ["calculateRelativeHumidity", "kernel.calculateRelativeHumidity", "aee_atmos_fnc_calculateRelativeHumidity", [50, 0, 20, 10, 0, 0], 1e-6, 0.5],
    ["calculateRelativeHumidity", "kernel.calculateRelativeHumidity", "aee_atmos_fnc_calculateRelativeHumidity", [60, 0, 15, 15, 0.8, 0], 1e-6, 0.5],
    ["calculateAirDensityKernel", "kernel.calculateAirDensityKernel", "aee_ballistics_fnc_calculateAirDensityKernel", [15, 1013.25, 50], 1e-6, 0],
    ["calculateAirDensityKernel", "kernel.calculateAirDensityKernel", "aee_ballistics_fnc_calculateAirDensityKernel", [30, 1000, 80], 1e-6, 0]
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
    private _bound = _abs + (_rel * abs _expected);

    private _nativeOut = "aee_dev" callExtension [_nativeName, _args];
    // arma-rs answers `callExtension [cmd, args]` with [output, errorCode, aux];
    // an absent extension answers with "".  A successful native call needs a
    // non-empty output and errorCode 0.
    private _nativePayload = "";
    private _nativeCode = 0;
    if (_nativeOut isEqualType []) then {
        _nativePayload = _nativeOut param [0, ""];
        _nativeCode = _nativeOut param [1, -1];
    } else {
        if (_nativeOut isEqualType "") then { _nativePayload = _nativeOut; };
    };
    if ((_nativePayload isEqualType "") && {_nativePayload != ""} && {_nativeCode isEqualType 0} && {_nativeCode == 0}) then {
        _nativeChecked = _nativeChecked + 1;
        private _actual = parseNumber _nativePayload;
        if ((abs (_expected - _actual)) <= _bound) then {
            _pass = _pass + 1;
        } else {
            _fail = _fail + 1;
            _notes pushBack format ["%1 native: expected %2 got %3 (bound %4)", _id, _expected, _actual, _bound];
        };
    } else {
        _nativeUnavailable = _nativeUnavailable + 1;
        private _fallbackOk = false;
        if (!isNil "_dispatch") then {
            private _dispatched = [_id, _args] call _dispatch;
            if ((_dispatched isEqualType 0) && {(abs (_expected - _dispatched)) <= _bound}) then {
                _fallbackOk = true;
            };
        };
        if (_fallbackOk) then {
            _pass = _pass + 1;
        } else {
            _fail = _fail + 1;
            _notes pushBack format ["%1 fallback: expected %2 (dispatch available %3)", _id, _expected, !isNil "_dispatch"];
        };
    };
} forEach _cases;

private _marker = if (_nativeChecked > 0) then { "native" } else { "native-unavailable" };
diag_log text format ["[P137] kernel path marker %1 (native %2, unavailable %3)", _marker, _nativeChecked, _nativeUnavailable];

if (_fail isEqualTo 0) then {
    diag_log text format ["[P137] [PASS] kernel parity: %1 checks, %2", _pass, _marker];
} else {
    diag_log text format ["[P137] [FAIL] kernel parity: %1 passed, %2 failed: %3", _pass, _fail, str _notes];
};
