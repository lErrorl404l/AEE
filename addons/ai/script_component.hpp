#define COMPONENT ai
#define COMPONENT_BEAUTIFIED AEE AI
#include "\z\aee\addons\lib\script_mod.hpp"
#include "\z\aee\addons\lib\script_macros.hpp"

// ── Disturbance field constants ───────────────────────────────────────────
// The field is a small grid of cells, each keyed by floor(pos / cell size)
// and holding the strongest recent stimulus.  Every numeric here is a
// modelling choice, UNSOURCED.  See the per-constant register in the
// wildlife-ambience dossier (docs/wiki/research/wildlife-ambience-dossier.md).
#define AI_CELL_SIZE 50
#define AI_STIMULUS_HALF_LIFE 45
#define AI_CELL_HORIZON 120
#define AI_CELL_CAP 256

// The stimulus broadcast rate limit, events per second.  Bounds the network
// cost of the gunfire report.
#define AI_BROADCAST_RATE 4

// The substrate client tick interval, seconds.
#define AI_TICK 1.0

// ── Engine-AI hearing constants ───────────────────────────────────────────
// AEE feeds the engine AI hearing from its single sound-propagation model,
// aee_weather_currentSoundPropagation, computed by
// addons/weather/functions/terrain/fnc_updateSoundPropagation.sqf.  The index
// (0.3 to 2.0, 1.0 baseline) scales the hearing range; no second propagation
// model is introduced.
//
// AI_HEARING_BASE_RANGE is the baseline hearing range in metres.  It is a
// modelling choice, UNSOURCED: the engine exposes no AI hearing range as a
// readable value.  The index scales it, so the effective range moves with the
// weather, not a constant.
#define AI_HEARING_BASE_RANGE 400

// The reveal value band.  The engine's reveal command sets the knowledge value
// to 1 when the revealing side holds none (engine command reference), and the
// value is capped below 1.5, the side-identification threshold: hearing alone
// never tells the AI which side fired.  Both bounds come from the engine and
// the issue, not a new model.
#define AI_HEARING_REVEAL_MIN 1.0
#define AI_HEARING_REVEAL_MAX 1.4
