#define COMPONENT thermal
#define COMPONENT_BEAUTIFIED AEE Thermal
#include "\z\aee\addons\main\script_mod.hpp"
#include "\z\aee\addons\main\script_macros.hpp"

// ── Fusion HUD drawn display (workshop 3810296503 whale_ecoti_llll) ─────────
// The compass tape and the glass tint are ported from the source RscTitles
// overlay and its functions/fn_drawHUD.sqf.  The geometry is fixed, exactly as
// the source fixed it: the display box is a square centred on the screen whose
// side is FUSION_HUD_BOX_FRACTION of the safe-zone height, and the tape scrolls
// across FUSION_HUD_TAPE_SPAN degrees to each side of the centre mark.
#define FUSION_HUD_BOX_FRACTION 0.40
#define FUSION_HUD_TAPE_FRACTION 0.40
#define FUSION_HUD_TAPE_SPAN 60
#define FUSION_HUD_SCALE 1.14
#define FUSION_HUD_Y 0.0
#define FUSION_HUD_BOOT_ON 1.05
#define FUSION_HUD_BOOT_OFF 0.70
// Fixed colours, RGBA.  The source locked these (fn_preInit.sqf) after removing
// the colour settings from its menu; they are constants, not runtime knobs.
#define FUSION_HUD_GLASS_COLOR [0.64, 0.31, 0.18, 0.15]
#define FUSION_HUD_RULER_COLOR [1.00, 0.30, 0.00, 0.60]
#define FUSION_HUD_INFO_COLOR [1.00, 0.30, 0.00, 0.60]
