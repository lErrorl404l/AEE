#define COMPONENT lighting
#define COMPONENT_BEAUTIFIED Lighting
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
// METEOR_SPEED_FACTOR.  The streak is drawn 6-9 km away, but real meteors
// ablate about 100 km up (70-120 km; Ceplecha et al. 1998, Space Sci. Rev.
// 84:327), so the speed is scaled by the distance ratio to keep the real
// angular rate across the sky.  METEOR_TICK must match the worker's PFH interval.
#define METEOR_TICK 0.25
#define METEOR_SPAWN_RADIUS_MIN 6000
#define METEOR_SPAWN_RADIUS_MAX 9000
// The flare IS the visible point, so its range must exceed the spawn radius
// or the meteor is never drawn (the starfield: flare 7500 > radius 5000).
#define METEOR_FLARE_MAX_DIST 12000
#define METEOR_LIGHT_BRIGHTNESS 3000
#define METEOR_LIGHT_DECAY 200
#define METEOR_LIFETIME 4
#define METEOR_HEIGHT 100000
#define METEOR_SPEED_FACTOR (((METEOR_SPAWN_RADIUS_MIN + METEOR_SPAWN_RADIUS_MAX) / 2) / METEOR_HEIGHT)

// ── Aurora curtain render (night-sky debug) ───────────────────────────────
// The two emission lines are sourced (NOAA SWPC Aurora Tutorial): 557.7 nm
// oxygen green (O I 1S-1D) and 630.0 nm oxygen red (O I 1D-3P).  The altitude
// band below is a render placement, not the published 90-400 km physical
// range.  The colours are the two lines' chromaticities (CIE 1931 2 deg,
// data/daylight/CIE_xyz_1931_2deg.csv: 557.7 nm x,y = 0.357, 0.640; 630.0 nm
// 0.708, 0.292) in sRGB (IEC 61966-2-1), brought into gamut by adding white
// (a spectral line lies outside every display gamut) and peak-normalised.
#define AURORA_TICK 0.5
#define AURORA_RENDER_RADIUS 12000
#define AURORA_BASE_ALT_M 2000
#define AURORA_BAND_ALT_M 4000
#define AURORA_GREEN [0.573,1.0,0.0]
#define AURORA_RED [1.0,0.0,0.271]

// ── Milky Way band render (night-sky debug) ───────────────────────────────
// The surface-brightness anchor is the published dark-sky value (21.8
// mag/arcsec^2, Crumey 2014); MILKY_WAY_NELM_MIN derives from that contrast.
// The colour, alpha, radius and sample count are render tunables (display preferences, no physical quantity).
#define MILKY_WAY_TICK 0.5
#define MILKY_WAY_NELM_MIN 5.0
#define MILKY_WAY_SAMPLES 96
#define MILKY_WAY_ALPHA 0.18
#define MILKY_WAY_RADIUS 5000
#define MILKY_WAY_COLOUR [0.70,0.72,0.85]

// ── Faint star bulk (night-sky debug) ────────────────────────────────────
// The light-emitter path caps at STAR_LIGHT_MAX_MAG; this layer draws the
// rest with drawLine3D.  Both values are performance tunables (no physical quantity).
#define FAINT_STAR_MAX 256
#define FAINT_STAR_RADIUS 5000
