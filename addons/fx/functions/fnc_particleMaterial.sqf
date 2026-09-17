#include "..\script_component.hpp"

/*
Particle material table (issue #150) — the physics parameters the engine
solver uses, keyed by particle material.

The engine IS the solver (gravity via weight, drag via volume, wind
coupling via rubbing, ground collision via bounceOnSurface).  AEE's job
is to feed it the RIGHT parameters for the material and the environment.
This function returns the material's BASE parameters; fnc_particleState
adds the environmental coupling (air density, ground state, wind).

Returns: [weight, volume, rubbing, bounceOnSurface, colour]

  weight  kg — gravity response (negative = buoyant: hot gas rises)
  volume  m3 — drag cross-section (air density scales the effect)
  rubbing 0..1 — wind coupling (0 = immune, 1 = fully advected)
  bounce  0..1 restitution (ground/water collision), -1 = no collision
  colour  RGBA array
*/

params [["_material", "smoke", [""]]];

private _tables = createHashMapFromArray [
    // Smoke: light, high drag, fully wind-advected, no bounce (puffs
    // dissipate on contact).
    ["smoke", [1.0, 1.0, 0.05, -1, [0.2, 0.2, 0.2, 0.8]]],
    // Dust: heavier, ground-hugging, bounces per ground state (the
    // coupling in fnc_particleState overrides bounce from groundState).
    ["dust", [1.0, 0.6, 0.5, 0.4, [0.45, 0.38, 0.3, 0.7]]],
    // Water spray: medium, high drag, surface-tracking (keepOnSurface),
    // splashes (bounce high).
    ["spray", [0.5, 2.0, 0.7, 0.8, [0.7, 0.75, 0.8, 0.6]]],
    // Debris: heavy, low drag, high bounce (fragments skitter).
    ["debris", [3.0, 0.2, 0.2, 0.6, [0.3, 0.28, 0.22, 1.0]]],
    // Fire/gas plume: NEGATIVE weight = buoyant (hot gas rises), low
    // drag, weakly wind-coupled (buoyancy dominates).
    ["plume", [-0.5, 0.5, 0.1, -1, [0.9, 0.6, 0.2, 0.9]]]
];

_tables getOrDefault [_material, _tables get "smoke"]
