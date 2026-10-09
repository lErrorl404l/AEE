#define COMPONENT thermal
#define COMPONENT_BEAUTIFIED AEE Thermal
#include "\z\aee\addons\lib\script_mod.hpp"
#include "\z\aee\addons\lib\script_macros.hpp"

// ── Fusion thermal-channel frame (issue #204, Track B ENVG-B) ───────────────
// Below this fraction the frame is a genuine inset.  At or above it the bars
// sit on the safe-zone edge and read as a border around the whole view, so the
// driver draws nothing (operator report 2026-10-03).
#define FUSION_FRAME_MIN_INSET 0.97

// ── Fusion HUD drawn display (workshop 3810296503 whale_ecoti_llll) ─────────
// The compass tape is ported from the source overlay and fn_drawHUD.sqf.  The
// source's ECOTI viewfinder box (config.cpp ecoti_tint, idc 910001) is a square
// centred on the screen whose side is FUSION_HUD_BOX_FRACTION of the safe-zone
// height (the source's fn_preInit.sqf boxSize 0.40 and fn_boxOnLoad.sqf
// geometry).  The source paints it as one translucent FILL; a full fill warms
// the green phosphor, so aee draws the same rectangle as its four EDGES in the
// source's own box colour (config.cpp ecoti_tint colorBackground
// {0.55, 0.08, 0.05, 0.30}) and the NVG stays green (operator report
// 2026-10-03).  The tape scrolls FUSION_HUD_TAPE_SPAN degrees each side.
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
// The source box colour (config.cpp ecoti_tint) and the edge thickness.  The
// source's outline width is 2 px at 1080p (fn_preInit.sqf "Outline Width");
// 0.0025 * safeZoneH is that width in safe-zone units and matches the fusion
// frame bar thickness.
#define FUSION_BOX_COLOR [0.55, 0.08, 0.05, 0.30]
#define FUSION_BOX_THICKNESS 0.0025
