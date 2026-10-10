#include "..\..\script_component.hpp"
/*
 * Fusion HUD compass tape show/hide (issue #204).
 *
 * Raises the GVAR(fusionHud) RscTitles display on its own layer, or clears it.
 * Idempotent: a call that matches the current state does nothing.  The onLoad
 * of that display stores the display handle in uiNamespace as
 * GVAR(fusionHudDisplay), where FUNC(hudTapeDraw) and FUNC(hudTapeInfo) find it.
 *
 * Ported from workshop 3810296503 whale_ecoti_llll functions/fn_showBox.sqf
 * (the cutRsc raise, the allControls clear and the cutText fallback).  The
 * source re-cut on every show to refresh a live glass size; aee fixes the glass
 * geometry, so one cut per session is enough.
 *
 * Params:
 *   0: _on (BOOL, default true) - true shows the display, false hides it.
 *
 * Returns: nothing.
 */
params [["_on", true, [true]]];

if (!hasInterface) exitWith {};

private _layer = ["aee_thermal_fusion_hud"] call BIS_fnc_rscLayer;
private _wasOn = missionNamespace getVariable [QGVAR(hudTapeOn), false];
if !(_wasOn isEqualType true) then { _wasOn = false; };

if (_on) then {
    if (_wasOn) exitWith {};
    _layer cutRsc [QGVAR(fusionHud), "PLAIN", -1, false];
    missionNamespace setVariable [QGVAR(hudTapeOn), true];
    // The display has just been rebuilt, so the tape's change cache must be
    // cleared, or the source's "nothing moved" skip leaves the rebuilt
    // controls blank for a frame.
    missionNamespace setVariable [QGVAR(hudTapeCache), []];
    private _logMsg = "fusion HUD: display raised";
    AEE_LOG_INFO(_logMsg);
} else {
    if (!_wasOn) exitWith {};
    private _disp = uiNamespace getVariable [QGVAR(fusionHudDisplay), displayNull];
    if (!isNull _disp) then {
        // Clearing the background is not enough: text is drawn on top of it,
        // so the text and its colour are wiped too (source fn_showBox.sqf).
        {
            _x ctrlSetBackgroundColor [0, 0, 0, 0];
            _x ctrlSetText "";
            _x ctrlSetTextColor [0, 0, 0, 0];
            _x ctrlCommit 0;
        } forEach (allControls _disp);
    };
    _layer cutText ["", "PLAIN"];
    missionNamespace setVariable [QGVAR(hudTapeOn), false];
    missionNamespace setVariable [QGVAR(hudTapeCache), []];
    private _logMsg = "fusion HUD: display cleared";
    AEE_LOG_INFO(_logMsg);
};
