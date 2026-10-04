#define COMPONENT ai
#define COMPONENT_BEAUTIFIED AEE AI
#include "\z\aee\addons\main\script_mod.hpp"
#include "\z\aee\addons\main\script_macros.hpp"

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
