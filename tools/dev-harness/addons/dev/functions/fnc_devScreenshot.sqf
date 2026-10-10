/*
fnc_devScreenshot - a labelled screenshot with a paired state line.

Writes aee_<label>_<timestamp>.png to <PROFILEDIR>\Screenshots and emits one
state line that names the file and the current AEE state, so a visual change
and the state that produced it are captured together. The DevScreenshot
keybind calls it.

Client only. A dedicated server renders nothing: the screenshot and the
visual verdict are a manual ceiling and no automated gate depends on the
image file. screenshot returns Boolean; a false result (no client render)
still emits the pairing line, so the gap is visible.

Arguments:
  0: _label <STRING> a short tag for the file name (default "manual").
Return Value: BOOL - the screenshot command result.
*/

if (!hasInterface) exitWith { false };

params [["_label", "manual", [""]]];

private _t = systemTime;
private _stamp = format [
    "%1%2%3-%4%5%6",
    _t select 0, _t select 1, _t select 2, _t select 3, _t select 4, _t select 5
];
private _name = format ["aee_%1_%2", _label, _stamp];

private _ok = screenshot _name;

// The paired state line: name the file, then emit the current AEE state.
private _state = [] call aee_diagnostics_fnc_dumpState;
private _logMsg = format [
    "dev screenshot | file=%1.png | result=%2 | state=%3",
    _name, _ok, if (isNil "_state") then { "core state line emitted" } else { str _state }
];
diag_log _logMsg;

_ok
