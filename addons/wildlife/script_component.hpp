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
// cached per-cell sample store.
#define WILDLIFE_ENVIRONMENT_QUERY_CAP 64
#define WILDLIFE_ENVIRONMENT_CAP 256
