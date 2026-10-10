// The dev channel starts only when the four-layer gate holds. Failure is a
// silent no-op: no per-frame handler, no verb table, no log line.
if !(call aee_dev_fnc_devGateLive) exitWith {};

aee_dev_verbs = call aee_dev_fnc_devVerbs;
aee_dev_funcs = call aee_dev_fnc_devFuncs;

// The extension raises this event for every request it forwards. The dispatcher
// parses the request literal and answers with the callExtension argument list.
// A refused or malformed request answers with an error and the handler stays up.
addMissionEventHandler ["ExtensionCallback", {
    params ["_name", "_function", "_data"];
    if (_name != "aee_dev") exitWith {};
    private _reply = [_function, _data] call aee_dev_fnc_devDispatch;
    if !(isNil "_reply") then {
        "aee_dev" callExtension _reply;
    };
}];

// Open the loopback listener. The extension refuses in a client build, so a
// client never opens a dev port.
"aee_dev" callExtension ["start", []];

// ─── Visual workbench keybinds ──────────────────────────────────────────────
// The category and the keys live in the dev project only. They are NOT part
// of the shipped settings taxonomy: no addons/*/initSettings.inc.sqf gains a
// dev setting. The handlers are compiled in XEH_preInit.
["AEE Dev", "DevReapplyVisual", ["Re-apply the visual state", "Re-read textures, materials and post-process effects"], {
    call aee_dev_fnc_devReapplyVisual;
}, {}] call CBA_fnc_addKeybind;

["AEE Dev", "DevScreenshot", ["Take a labelled screenshot", "Write aee_<label>_<time>.png and a paired state line"], {
    call aee_dev_fnc_devScreenshot;
}, {}] call CBA_fnc_addKeybind;

["AEE Dev", "DevDump", ["Dump every module state", "Emit one state line per module from the debug index"], {
    call aee_dev_fnc_devDumpAll;
}, {}] call CBA_fnc_addKeybind;

["AEE Dev", "DevOverlayToggle", ["Toggle the dev overlay", "Show or hide the on-screen state panel"], {
    call aee_dev_fnc_devOverlayToggle;
}, {}] call CBA_fnc_addKeybind;
