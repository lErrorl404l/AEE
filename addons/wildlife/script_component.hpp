#define COMPONENT wildlife
#define COMPONENT_BEAUTIFIED AEE Wildlife
#include "\z\aee\addons\main\script_mod.hpp"
#include "\z\aee\addons\main\script_macros.hpp"

// Modelling constants, UNSOURCED.  See the wildlife-ambience dossier.
#define WILDLIFE_SOUND_INSTANCE_CAP 8
#define WILDLIFE_SOUND_MAX_DISTANCE 120
#define WILDLIFE_ANIMAL_CAP 16

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
