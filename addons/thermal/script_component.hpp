#define COMPONENT thermal
#define COMPONENT_BEAUTIFIED AEE Thermal
#include "\z\aee\addons\main\script_mod.hpp"
#include "\z\aee\addons\main\script_macros.hpp"

// ── Fusion thermal-channel frame (issue #204, Track B ENVG-B) ───────────────
// Below this fraction the frame is a genuine inset.  At or above it the bars
// sit on the safe-zone edge and read as a border around the whole view, so the
// driver draws nothing (operator report 2026-10-03).
#define FUSION_FRAME_MIN_INSET 0.97

// ── Fusion HUD drawn display (workshop 3810296503 whale_ecoti_llll) ─────────
// The compass tape is ported from the source overlay and fn_drawHUD.sqf.  The
// source's translucent "glass" panel is NOT ported: it tinted the whole NVG
// image (operator report 2026-10-03).  The box is a square centred on the
// screen, FUSION_HUD_BOX_FRACTION of safe-zone height; the tape scrolls
// FUSION_HUD_TAPE_SPAN degrees each side of the mark.
#define FUSION_HUD_BOX_FRACTION 0.40
#define FUSION_HUD_TAPE_FRACTION 0.40
#define FUSION_HUD_TAPE_SPAN 60
#define FUSION_HUD_SCALE 1.14
#define FUSION_HUD_Y 0.0
#define FUSION_HUD_BOOT_ON 1.05
#define FUSION_HUD_BOOT_OFF 0.70
// Fixed colours, RGBA.  The source locked these (fn_preInit.sqf) after removing
// the colour settings from its menu; they are constants, not runtime knobs.
#define FUSION_HUD_RULER_COLOR [1.00, 0.30, 0.00, 0.60]
#define FUSION_HUD_INFO_COLOR [1.00, 0.30, 0.00, 0.60]
