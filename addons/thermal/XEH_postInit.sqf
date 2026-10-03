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
