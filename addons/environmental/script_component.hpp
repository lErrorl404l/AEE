#define COMPONENT environmental
#define COMPONENT_BEAUTIFIED AEE Environmental
#include "\z\aee\addons\lib\script_mod.hpp"
#include "\z\aee\addons\lib\script_macros.hpp"

// ── Celestial render (issue #122) ────────────────────────────────────────
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

// ── Aurora curtain render (night-sky debug) ───────────────────────────────
// The two emission lines are sourced (NOAA SWPC Aurora Tutorial): 557.7 nm
// oxygen green (O I 1S-1D) and 630.0 nm oxygen red (O I 1D-3P).  The altitude
// band below is a render tunable, not the published 90-400 km physical range,
// and every geometry and colour value here is UNSOURCED except the two lines.
#define AURORA_TICK 0.5
#define AURORA_RENDER_RADIUS 12000
#define AURORA_BASE_ALT_M 2000
#define AURORA_BAND_ALT_M 4000
#define AURORA_GREEN [0.35,1.0,0.45]
#define AURORA_RED [1.0,0.30,0.35]

// ── Milky Way band render (night-sky debug) ───────────────────────────────
// The surface-brightness anchor is the published dark-sky value (21.8
// mag/arcsec^2, Crumey 2014); MILKY_WAY_NELM_MIN derives from that contrast.
// The colour, alpha, radius and sample count are render tunables, UNSOURCED.
#define MILKY_WAY_TICK 0.5
#define MILKY_WAY_NELM_MIN 5.0
#define MILKY_WAY_SAMPLES 96
#define MILKY_WAY_ALPHA 0.18
#define MILKY_WAY_RADIUS 5000
#define MILKY_WAY_COLOUR [0.70,0.72,0.85]

// ── Faint star bulk (night-sky debug) ────────────────────────────────────
// The light-emitter path caps at STAR_LIGHT_MAX_MAG; this layer draws the
// rest with drawLine3D.  Both values are performance tunables, UNSOURCED.
#define FAINT_STAR_MAX 256
#define FAINT_STAR_RADIUS 5000
