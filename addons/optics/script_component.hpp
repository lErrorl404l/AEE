#define COMPONENT optics
#define COMPONENT_BEAUTIFIED AEE Optics
#include "\z\aee\addons\main\script_mod.hpp"
#include "\z\aee\addons\main\script_macros.hpp"

// ── Dynamic starfield render (issue #122) ─────────────────────────────────
// The engine caps concurrent dynamic lights, so #lightpoint is viable only
// for the bright stars; the faint bulk needs a Draw3D primitive (not yet
// shipped).  This is the magnitude ceiling for the light-emitter path.
#define STAR_LIGHT_MAX_MAG 2.0

// ── Meteor shower render (issue #122) ────────────────────────────────────
// Render tunables for the client #lightpoint + #particlesource worker.
// The worker converts V-infinity (km/s) to m/s, then scales by
// METEOR_SPEED_FACTOR for a visible streak; that factor is UNSOURCED and
// chosen for the eye.  METEOR_TICK must match the worker's PFH interval.
#define METEOR_TICK 0.25
#define METEOR_SPAWN_RADIUS_MIN 6000
#define METEOR_SPAWN_RADIUS_MAX 9000
// The flare IS the visible point, so its range must exceed the spawn radius
// or the meteor is never drawn (the starfield: flare 7500 > radius 5000).
#define METEOR_FLARE_MAX_DIST 12000
#define METEOR_LIGHT_BRIGHTNESS 3000
#define METEOR_LIGHT_DECAY 200
#define METEOR_LIFETIME 4
#define METEOR_SPEED_FACTOR 0.01
