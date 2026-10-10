#define COMPONENT ltm
#define COMPONENT_BEAUTIFIED AEE LTM
#include "\z\aee\addons\lib\script_mod.hpp"

// #define DEBUG_MODE_FULL

#ifdef DEBUG_ENABLED_AEE_LTM
    #define DEBUG_MODE_FULL
#endif

#include "\z\aee\addons\lib\script_macros.hpp"

// ── Laser target marker (LTM) ──────────────────────────────────────────────
// Ported from workshop 2041057379 A3TI/LTM.  The beam marks a laser
// designator target and is visible through night vision.  Blink and steady
// are the two source modes.
#define LTM_MODE_BLINK 0
#define LTM_MODE_STEADY 1
#define LTM_BLINK_INTERVAL 0.3
#define LTM_SEGMENT_COUNT 21
#define LTM_SEGMENT_STEP 500
