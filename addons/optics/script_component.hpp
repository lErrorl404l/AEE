#define COMPONENT optics
#define COMPONENT_BEAUTIFIED AEE Optics
#include "\z\aee\addons\main\script_mod.hpp"
#include "\z\aee\addons\main\script_macros.hpp"

// ── Dynamic starfield render (issue #122) ─────────────────────────────────
// The engine caps concurrent dynamic lights, so #lightpoint is viable only
// for the bright stars; the faint bulk needs a Draw3D primitive (not yet
// shipped).  This is the magnitude ceiling for the light-emitter path.
#define STAR_LIGHT_MAX_MAG 2.0
