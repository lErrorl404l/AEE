/*
fnc_devOverlayToggle - toggle the optional on-screen dev panel.

When the panel is on, a one-second handler renders the dump-all lines to the
screen with hintSilent. The panel renders existing dump output only: it
defines no new state and no second monitor (no separate display or map).

Client only.

Arguments: none.
Return Value: BOOL - true when the panel is now on.
*/

if (!hasInterface) exitWith { false };

private _handle = missionNamespace getVariable ["aee_dev_overlayPFH", -1];

if (_handle >= 0) exitWith {
    [_handle] call CBA_fnc_removePerFrameHandler;
    missionNamespace setVariable ["aee_dev_overlayPFH", -1];
    hintSilent "";
    false
};

private _newHandle = [{
    private _lines = [] call aee_dev_fnc_devDumpAll;
    hintSilent (_lines joinString endl);
}, 1] call CBA_fnc_addPerFrameHandler;

missionNamespace setVariable ["aee_dev_overlayPFH", _newHandle];
true
