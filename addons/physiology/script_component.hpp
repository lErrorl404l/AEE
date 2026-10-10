#define COMPONENT physiology
#define COMPONENT_BEAUTIFIED AEE Physiology
#include "\z\aee\addons\lib\script_mod.hpp"
#include "\z\aee\addons\lib\script_macros.hpp"

// ── Combat-stress psychology array (issue #110) ───────────────────────────
// The per-unit state the driver publishes under QGVAR(psychology).  The AI
// behaviour layer reads it by index.  The kernels are in aee_strain
// (functions/psychology); the driver is state/updatePsychologyState.
#define PSY_I_STRESS 0
#define PSY_I_MORALE 1
#define PSY_I_MULT_REACTION 2
#define PSY_I_MULT_ACCURACY 3
#define PSY_I_MULT_SPOTTING 4
#define PSY_I_MULT_FIRING 5
#define PSY_I_EFF_SPOTTING 6
#define PSY_I_ACTION 7
