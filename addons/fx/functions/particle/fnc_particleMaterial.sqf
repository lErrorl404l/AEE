#include "..\..\script_component.hpp"

/*
Particle material table (issues #149, #150) — the ONE source of truth for
the base physics parameters of a particle material.

The engine IS the solver: gravity acts on weight, drag on volume, the wind
on rubbing, and the ground on bounceOnSurface.  AEE's job is to give the
engine the right numbers for the material.  This table holds the BASE
numbers; fnc_particleState adds the environmental coupling and
fnc_kickupParams adds the surface-lift term.  Both read this table, so the
numbers cannot drift between callers.

Columns: [weight, volume, rubbing, bounce, colour]
  weight  kg    - gravity response.  Negative = buoyant (hot gas rises).
  volume  m3    - drag cross-section.  Air density scales the effect.
  rubbing 0..1  - wind coupling (0 = immune, 1 = fully advected).
  bounce  0..1  - ground restitution; -1 disables ground collision.
  colour  RGBA  - fallback tint when the surface cannot be sampled.

The surface materials (dust, sand, dirt, snow, mud, gravel, spray) keep the
values the live kickup functions already used, so migrating them to the
pipeline does not change their behaviour.  The extra materials (smoke,
debris, plume, hail, rain) serve the fire, explosion and weather effects.
Hail is heavy with a low drag and a high bounce: the issue gives
bounceOnSurface 0.6 for real hail (#151).

Argument:
  0: material (STRING, default "dust")

Returns: [weight, volume, rubbing, bounce, colour]
*/

params [["_material", "dust", [""]]];

private _tables = createHashMapFromArray [
    // Fine mineral dust: slow settling, high drag, wind-following.
    ["dust",   [1.00, 0.60, 0.50, 0.25, [0.62, 0.58, 0.48, 1]]],
    // Sand grains: heavier, settle quickly, still wind-driven.
    ["sand",   [1.45, 0.45, 0.42, 0.20, [0.85, 0.76, 0.55, 1]]],
    // Dry organic soil: light and fluttery, travels far.
    ["dirt",   [1.10, 0.70, 0.55, 0.15, [0.44, 0.34, 0.23, 1]]],
    // Snow crystals: very light, large area per mass, long drift.
    ["snow",   [0.55, 1.10, 0.75, 0.05, [1.00, 1.00, 1.00, 1]]],
    // Wet clods: heavy, low drag, little transport, no bounce.
    ["mud",    [1.60, 0.30, 0.20, 0.05, [0.30, 0.24, 0.17, 1]]],
    // Gravel and scree: dense, settles at once.
    ["gravel", [1.80, 0.25, 0.15, 0.35, [0.54, 0.52, 0.49, 1]]],
    // Water spray: atomised, high drag, surface-tracking.
    ["spray",  [0.80, 1.40, 0.35, 0.60, [0.72, 0.78, 0.82, 1]]],
    // Smoke: light, high drag, fully wind-advected, no ground collision.
    ["smoke",  [1.00, 1.00, 0.05, -1,   [0.20, 0.20, 0.20, 0.8]]],
    // Debris: heavy, low drag, high bounce (fragments skitter).
    ["debris", [3.00, 0.20, 0.20, 0.60, [0.30, 0.28, 0.22, 1]]],
    // Fire/gas plume: NEGATIVE weight = buoyant (hot gas rises).
    ["plume",  [-0.50, 0.50, 0.10, -1,  [0.90, 0.60, 0.20, 0.9]]],
    // Hail: dense ice, low drag, bounces (0.6 per issue #151).
    ["hail",   [2.20, 0.15, 0.10, 0.60, [0.92, 0.95, 1.00, 1]]],
    // Rain drop: light, high drag, wind-following, no ground bounce.
    ["rain",   [0.90, 1.30, 0.80, -1,   [0.70, 0.78, 0.88, 1]]]
];

_tables getOrDefault [_material, _tables get "dust"]
