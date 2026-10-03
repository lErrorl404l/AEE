#define COMPONENT nightvision
#define COMPONENT_BEAUTIFIED AEE Night Vision
#include "\z\aee\addons\main\script_mod.hpp"
#include "\z\aee\addons\main\script_macros.hpp"

// ── Laser target marker (LTM) ──────────────────────────────────────────────
// Ported from workshop 2041057379 A3TI/LTM.  The beam marks a laser
// designator target and is visible through night vision.  Blink and steady
// are the two source modes.  See functions/ltm/.
#define LTM_MODE_BLINK 0
#define LTM_MODE_STEADY 1
#define LTM_BLINK_INTERVAL 0.3
#define LTM_SEGMENT_COUNT 21
#define LTM_SEGMENT_STEP 500
