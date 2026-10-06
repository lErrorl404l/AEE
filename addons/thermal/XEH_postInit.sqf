#include "script_component.hpp"
#include "\z\aee\addons\main\script_debug.hpp"

AEE_MODULE_POST_INIT

// ── Fusion outline worker ──────────────────────────────────────────────────
// The outline is drawn on a full-screen transparent map control from its own
// Draw event handler (FUNC(outlineCanvas)).  The segments that handler draws
// are computed by FUNC(outlineDraw).  In the source (workshop 3811605241
// whale_ecoti_llll functions/fn_postInit.sqf) that worker runs on the mission
// Draw3D event; aee raised the display but never registered a caller, so the
// canvas stayed empty and the outline was silent (no "fusion outline" line in
// the RPT).  Register the worker once here.  It early-exits unless the setting
// and the fusion mode are on, so the idle cost is one getVariable read a frame.
if (hasInterface && {isNil QGVAR(outlineEH)}) then {
    missionNamespace setVariable [QGVAR(outlineEH), addMissionEventHandler ["Draw3D", {
        [] call FUNC(outlineDraw);
        // The drawn fusion display (workshop 3810296503 whale_ecoti_llll).
        // FUNC(hudTapeBoot) owns the display lifetime and its brightness
        // envelope; FUNC(hudTapeDraw) draws the compass tape.  Both early-exit
        // unless the display is up, so an operator without fusion pays two
        // getVariable reads a frame.  The source ran the same pair from its
        // mission Draw3D handler (fn_postInit.sqf).
        [] call FUNC(hudTapeBoot);
        [] call FUNC(hudTapeDraw);
        [] call FUNC(hudBoxDraw);
    }]];
    // The corner readouts refresh at 0.1 s; a clock and a grid square do not
    // need a per-frame redraw (source ran fn_drawInfo on its 0.10 s loop).
    [FUNC(hudTapeInfo), 0.1] call CBA_fnc_addPerFrameHandler;
    private _logMsg = "fusion display: Draw3D worker and HUD tape registered";
    AEE_LOG_INFO(_logMsg);
};

// ── Active IR illuminator (issue #196) ────────────────────────────────────
// The keybind flips the CBA setting; the per-second driver owns the light.
// UNSOURCED mechanism: a workshop idea re-implemented as AEE code.
["AEE", "ActiveIRToggle", [LLSTRING(activeIRToggle), "Toggle the active-IR illuminator"], {
    private _on = missionNamespace getVariable [QGVAR(activeIR), false];
    [QGVAR(activeIR), !_on, 0, "client", true] call CBA_settings_fnc_set;
}, {}, [0, [false, false, false]]] call CBA_fnc_addKeybind;

if (hasInterface) then {
    // Death and respawn destroy the light, so it never survives a unit change.
    // The per-second driver detects both as well, so a missed event cannot leak.
    player addEventHandler ["Killed", { [] call FUNC(stopActiveIR); }];
    player addEventHandler ["Respawn", { [] call FUNC(stopActiveIR); }];
    [FUNC(applyActiveIR), 1] call CBA_fnc_addPerFrameHandler;
};
