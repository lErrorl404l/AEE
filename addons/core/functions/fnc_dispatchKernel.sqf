#include "..\script_component.hpp"

/*
Single kernel dispatcher (Pillar 2 - the kernel interface dispatcher).

Every pure kernel is called through this one function name, so the SQF
reference kernel and a future native kernel are interchangeable behind it.

The native path is taken only when the extension was proven ready (QGVAR(extReady)).
An arma-rs extension answers `callExtension [command, args]` with the array
`[output, errorCode, aux]`: the call succeeds only when the output is a
non-empty string and errorCode is 0.  An absent extension answers with an empty
string instead.  Any other result selects the SQF kernel.

The engine loads an extension lazily, so the init probe can run before the
extension is ready.  When init left QGVAR(extReady) false, the dispatcher
re-probes ONCE on the first dispatch.  The one-shot flag keeps every later
dispatch free of callExtension when the extension is truly absent.

Arguments:
  0: kernel id (STRING, a row in QGVAR(kernelTable))
  1: kernel arguments (ARRAY)

Returns: the kernel result, from the native path when selected, else the SQF
reference kernel.
*/

params [["_kernel", "", [""]], ["_args", [], [[]]]];

private _table = missionNamespace getVariable [QGVAR(kernelTable), createHashMap];
private _entry = _table getOrDefault [_kernel, []];
if ((count _entry) < 2) exitWith { nil };

private _sqfRef = _entry select 0;
private _nativeName = _entry select 1;

// Native only when the extension was proven ready.  When init left it false,
// probe ONCE more on the first dispatch: the engine loads an extension lazily,
// so the extension may answer only now.  The one-shot flag keeps every later
// dispatch free of callExtension when the extension is truly absent.
private _nativeOutput = "";
private _ready = missionNamespace getVariable [QGVAR(extReady), false];
if (!_ready && {!(missionNamespace getVariable [QGVAR(extLateProbe), false])}) then {
    missionNamespace setVariable [QGVAR(extLateProbe), true];
    [] call FUNC(probeExtension);
    _ready = missionNamespace getVariable [QGVAR(extReady), false];
};
if (_ready) then {
    private _result = (missionNamespace getVariable [QGVAR(extName), "aee_dev"]) callExtension [_nativeName, _args];
    // arma-rs answers `callExtension [command, args]` with [output, errorCode,
    // aux]; an absent extension answers with "".  A successful call needs a
    // non-empty output and errorCode 0.
    private _output = "";
    private _code = 0;
    if (_result isEqualType []) then {
        _output = _result param [0, ""];
        _code = _result param [1, -1];
    } else {
        if (_result isEqualType "") then { _output = _result; };
    };
    if ((_output isEqualType "") && {_output != ""} && {_code isEqualType 0} && {_code == 0}) then {
        _nativeOutput = _output;
    };
};

// The native return wins only when it is a non-empty string with errorCode 0.
// The exitWith sits at the function scope: a bare exitWith inside a `then`
// block does not return from the function, it only leaves that block.
if (_nativeOutput != "") exitWith { _nativeOutput };

// SQF reference kernel: the fallback and the parity oracle for the native path.
// The arguments array is spread onto the kernel's positional params.
_args call (missionNamespace getVariable [_sqfRef, { nil }]);
