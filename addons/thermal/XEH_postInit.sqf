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
    }]];
    private _logMsg = "fusion outline: Draw3D worker registered";
    AEE_LOG_INFO(_logMsg);
};
