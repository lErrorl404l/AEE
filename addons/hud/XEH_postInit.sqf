#include "script_component.hpp"

AEE_MODULE_POST_INIT

// ── ECOTI environment HUD ─────────────────────────────────────────────────
// Two Draw3D workers (rangefinder, map markers) and the update PFHs.  Every
// worker gates on the aee_hud_hudEnabled setting each tick, so the HUD toggles
// live and an operator who leaves it OFF pays one getVariable read per tick.
// Ported from workshop 3759527903 FPANO_ECOTI.  hasInterface only: the display
// and the raycasts are client-side.
if (hasInterface) then {
    [] call FUNC(hudRangefinder);
    [] call FUNC(hudMarkers);
    [FUNC(hudUpdate), 0.1] call CBA_fnc_addPerFrameHandler;
    // Signal-dependent tracker: the driver publishes the per-track state and
    // the draw layer renders it on the map and the HUD.  Both gate on the
    // aee_hud_trackerEnabled setting each tick.
    [] call FUNC(trackerDraw);
    [FUNC(trackerUpdate), 0.1] call CBA_fnc_addPerFrameHandler;
};
