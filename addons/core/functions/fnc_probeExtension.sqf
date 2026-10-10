#include "..\script_component.hpp"

/*
Probe the native dev extension and cache the verdict in QGVAR(extReady).

An arma-rs extension answers `callExtension [command, args]` with the array
`[output, errorCode, aux]`; the call succeeds when the output is a non-empty
string and errorCode is 0.  An absent extension answers with an empty string
instead.  Both shapes are accepted here, so the verdict is true only for a
ready extension that answered with an errorCode of 0.

The engine loads an extension lazily, on the first call that names it, so a
probe can run before the extension is ready.  The dispatcher re-probes once on
the first dispatch for that case.  When the extension is absent QGVAR(extReady)
stays false, and after that one-shot probe the hot path never calls the engine.

The extension is dev-only (ADR-035); it ships in no release artefact.
*/

private _extName = "aee_dev";
private _probe = _extName callExtension ["__probe__", []];

private _output = "";
private _code = 0;
if (_probe isEqualType []) then {
    _output = _probe param [0, ""];
    _code = _probe param [1, -1];
} else {
    if (_probe isEqualType "") then { _output = _probe; };
};
if !(_output isEqualType "") then { _output = ""; };

private _ready = (_output != "") && {_code isEqualType 0} && {_code == 0};

missionNamespace setVariable [QGVAR(extName), _extName];
missionNamespace setVariable [QGVAR(extReady), _ready];
