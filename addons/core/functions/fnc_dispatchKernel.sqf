#include "..\script_component.hpp"

/*
Single kernel dispatcher (Pillar 2 - the kernel interface dispatcher).

Every pure kernel is called through this one function name, so the SQF
reference kernel and a future native kernel are interchangeable behind it.

The native path is taken only when the extension was proven ready at preInit
(QGVAR(extReady)) AND the native return is non-empty with errorCode 0.  An
absent extension or a failed call returns an empty string, so the SQF kernel
runs.  When the extension is absent, no callExtension happens on the hot path.

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

// Native only when the preInit probe proved the extension ready.  The guard is
// what keeps callExtension off the hot path when the extension is absent.
if (missionNamespace getVariable [QGVAR(extReady), false]) then {
    private _out = (missionNamespace getVariable [QGVAR(extName), "aee_dev"]) callExtension [_nativeName, _args];
    if ((_out isEqualType "") && {_out != ""}) exitWith { _out };
};

// SQF reference kernel: the fallback and the parity oracle for the native path.
[_args] call (missionNamespace getVariable [_sqfRef, { nil }]);
