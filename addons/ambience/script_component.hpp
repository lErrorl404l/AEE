#define COMPONENT ambience
#define COMPONENT_BEAUTIFIED AEE Ambience
#include "\z\aee\addons\lib\script_mod.hpp"

// #define DEBUG_MODE_FULL

#ifdef DEBUG_ENABLED_AEE_AMBIENCE
    #define DEBUG_MODE_FULL
#endif

#include "\z\aee\addons\lib\script_macros.hpp"

// Modelling constants used by the ambience kernels.  Split out of aee_wildlife
// (ADR-032); the shared values are mirrored from the wildlife header, the same
// pattern aee_wildlife uses for AI_CELL_CAP.  UNSOURCED unless the kernel cites
// a source.
#define WILDLIFE_ACOUSTIC_EVENT_CAP 64
#define WILDLIFE_ACOUSTIC_EVENT_HORIZON 3
#define WILDLIFE_ACOUSTIC_HEARING_FLOOR_DB 30
#define WILDLIFE_ACOUSTIC_LOUD_DB 140
#define WILDLIFE_ACOUSTIC_OCCLUSION_DB 6
#define WILDLIFE_ACOUSTIC_OCCLUSION_RADIUS_M 2.5
#define WILDLIFE_CALL_BUDGET 256
#define WILDLIFE_CALL_HORIZON 120
#define WILDLIFE_EMITTER_CAP 3
#define WILDLIFE_EMITTER_RADIUS 150
#define WILDLIFE_PITCH_JITTER 0.04
#define WILDLIFE_PITCH_MAX 2.0
#define WILDLIFE_PITCH_MIN 0.5
#define WILDLIFE_PITCH_RATE_COUPLING 0.25
#define WILDLIFE_SHOT_CRACK_DB 150
#define WILDLIFE_SHOT_PITCH_PER_MACH 0.15
#define WILDLIFE_SHOT_REPORT_DB 160
#define WILDLIFE_SHOT_REPORT_REF_MV 900
#define WILDLIFE_SHOT_RICOCHET_ANGLE_DEG 30
#define WILDLIFE_SHOT_RICOCHET_DB 130
#define WILDLIFE_SHOT_RICOCHET_REF_J 500
#define WILDLIFE_SHOT_SNAP_DB 140
#define WILDLIFE_SHOT_SNAP_RADIUS_M 5
#define WILDLIFE_SOUND_INSTANCE_CAP 3
#define WILDLIFE_SOUND_MAX_DISTANCE 120

