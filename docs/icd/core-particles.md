# ICD: core to particles

- Producer CI: `addons/core/`
- Consumer CI: `addons/particles/`
- Direction: one way. `core` must initialise before `particles` reads.
- Variables crossing: 11.

A variable named `aee_core_{leaf}` is written as `EGVAR(core,leaf)` by the producer and read as `EGVAR(core,leaf)` or `QEGVAR(core,leaf)` by the consumer.

| Variable | Type | Unit | Range | Update | Evidence (first read) | Purpose (Annex C) |
|---|---|---|---|---|---|---|
| `aee_core_biome` | STRING | code | UNKNOWN | UNKNOWN | `addons/particles/functions/particle/fnc_particleEmission.sqf:46` | Koppen biome code (map climate class) |
| `aee_core_currentAirDensity` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/particles/functions/particle/fnc_calculateDownwash.sqf:82` | Air density in kg/m3 |
| `aee_core_currentBlowingSnow` | SCALAR | fraction | 0..1 | UNKNOWN | `addons/particles/functions/particle/fnc_particleEmission.sqf:89` | Blowing snow 0..1 |
| `aee_core_currentHumidity` | SCALAR | percent | 0..100 | UNKNOWN | `addons/particles/functions/particle/fnc_particlePipelineEmit.sqf:88` | Relative humidity percent |
| `aee_core_currentSandstorm` | SCALAR | fraction | 0..1 | UNKNOWN | `addons/particles/functions/particle/fnc_particleEmission.sqf:103` | Sandstorm intensity 0..1 |
| `aee_core_currentWindStr` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/particles/functions/particle/fnc_particleEmission.sqf:41` | UNKNOWN |
| `aee_core_dustSuppression` | SCALAR | fraction | 0..1 | UNKNOWN | `addons/particles/functions/particle/fnc_particleEmission.sqf:39` | Dust suppression 0..1 |
| `aee_core_groundState` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/particles/functions/particle/fnc_particleEmission.sqf:69` | Ground state |
| `aee_core_hailActive` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/particles/functions/particle/fnc_particleEmission.sqf:97` | Hail gate: convective instability + wet-bulb below freezing aloft (#151) |
| `aee_core_precipitationPhase` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/particles/functions/particle/fnc_particleEmission.sqf:82` | Phase (rain/sleet/snow/freezing_rain) |
| `aee_core_snowfallRate` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/particles/functions/particle/fnc_particleEmission.sqf:83` | Snowfall rate |

The default value and the update frequency are the producer's contract. They are set in the producer's CBA settings and recorded in `docs/wiki/annexes/annex-c-variable-reference.qmd`. This document records the boundary and the direction, not a second copy of the variable reference.

Regenerate with `python3 tools/architecture/interface_contracts.py`.
