#define COMPONENT wildlife
#define COMPONENT_BEAUTIFIED AEE Wildlife
#include "\z\aee\addons\main\script_mod.hpp"
#include "\z\aee\addons\main\script_macros.hpp"

// Modelling constants, UNSOURCED.  See the wildlife-ambience dossier.
//
// The concurrent one-shot cap is a density choice.  The acoustic niche
// hypothesis (Krause 1987; Pijanowski et al. 2011, BioScience 61(3):203-216)
// holds that species partition the auditory spectrum in time and frequency, so
// a real forest has few overlapping calls.  No published figure gives a
// simultaneous-caller count, so the cap is a stated choice: 3, the number of
// species groups active in the densest corpus bin.  The measured density was
// 8 of 8 slots busy at once, which reads as a disturbed soundscape.
#define WILDLIFE_SOUND_INSTANCE_CAP 3
#define WILDLIFE_SOUND_MAX_DISTANCE 120
#define WILDLIFE_ANIMAL_CAP 16

// Attached emitter policy (task T27).  The cap bounds the attached looping
// sources and the radius bounds which animals are near enough to carry one,
// so the attachment cost is flat.  Both are UNSOURCED modelling choices.  The
// cap is the same density target as the one-shot layer above.
#define WILDLIFE_EMITTER_CAP 3
#define WILDLIFE_EMITTER_RADIUS 150

// Call-pitch policy (task T28): bounds, seeded jitter spread and the
// stridulation coupling to the Dolbear rate.  All UNSOURCED; the speed of
// sound against temperature is SOURCED in fnc_callPitch.
#define WILDLIFE_PITCH_MIN 0.5
#define WILDLIFE_PITCH_MAX 2.0
#define WILDLIFE_PITCH_JITTER 0.04
#define WILDLIFE_PITCH_RATE_COUPLING 0.25

// Shot-audio policy (task T26).  The speed of sound against temperature is
// SOURCED (20.05*sqrt(T_K), the same convention as the ballistics drag and
// Mach-cone kernels).  The report reference, the pitch slope, and the crack,
// snap and ricochet levels and geometry bounds are UNSOURCED.
#define WILDLIFE_SHOT_REPORT_DB 160
#define WILDLIFE_SHOT_REPORT_REF_MV 900
#define WILDLIFE_SHOT_PITCH_PER_MACH 0.15
#define WILDLIFE_SHOT_CRACK_DB 150
#define WILDLIFE_SHOT_SNAP_RADIUS_M 5
#define WILDLIFE_SHOT_SNAP_DB 140
#define WILDLIFE_SHOT_RICOCHET_DB 130
#define WILDLIFE_SHOT_RICOCHET_ANGLE_DEG 30
#define WILDLIFE_SHOT_RICOCHET_REF_J 500

// The disturbance field policy is owned by aee_ai.  The wildlife tick is the
// only cross-addon consumer, so the cap and the horizon are mirrored here
// rather than reaching into the aee_ai header.  Keep them in step with
// addons/ai/script_component.hpp and the per-constant register.
#define AI_CELL_CAP 256
#define AI_CELL_HORIZON 120

// Neighbourhood environment sampler policy.  Modelling choices, UNSOURCED.
// The query cap bounds the object queries per call; the cell cap bounds the
// cached per-cell sample store.  The horizon mirrors AI_CELL_HORIZON and the
// half-life mirrors AI_STIMULUS_HALF_LIFE, so the environment cache ages like
// the disturbance field.
#define WILDLIFE_ENVIRONMENT_QUERY_CAP 64
#define WILDLIFE_ENVIRONMENT_CAP 256
#define WILDLIFE_ENVIRONMENT_HORIZON 120
#define WILDLIFE_ENVIRONMENT_HALF_LIFE 45

// The spawn suitability floor.  A group below it is not spawned.  UNSOURCED.
#define WILDLIFE_SUITABILITY_MIN 0.2

// Acoustic propagation policy (task T25).  The spreading law is the SOURCED
// inverse-square law: a point source loses 20*log10(d) dB, so 6 dB per
// doubling of distance.  The occlusion loss and radius, the hearing floor and
// the loud reference are UNSOURCED modelling choices.  The source levels live
// in fnc_acousticSourceDb.sqf.  See the per-constant register in the dossier.
#define WILDLIFE_ACOUSTIC_EVENT_CAP 64
#define WILDLIFE_ACOUSTIC_EVENT_HORIZON 3
#define WILDLIFE_ACOUSTIC_OCCLUSION_DB 6
#define WILDLIFE_ACOUSTIC_OCCLUSION_RADIUS_M 2.5
#define WILDLIFE_ACOUSTIC_HEARING_FLOOR_DB 30
#define WILDLIFE_ACOUSTIC_LOUD_DB 140

// The spook threshold on the propagated level, 0 to 1.  UNSOURCED.
#define WILDLIFE_SPOOK_ACOUSTIC_MIN 0.5

// Cognition policy (tasks T16 and T17).  UNSOURCED modelling choices: the
// count budget caps the animals visited per ecology tick; the call bus cap
// and horizon mirror the disturbance field so the bus ages like the field.
#define WILDLIFE_COGNITION_BATCH 8
#define WILDLIFE_CALL_RANGE 200
#define WILDLIFE_CALL_BUDGET 256
#define WILDLIFE_CALL_HORIZON 120
#define WILDLIFE_CALL_HALF_LIFE 45
