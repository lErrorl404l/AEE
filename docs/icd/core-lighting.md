# ICD: core to lighting

- Producer CI: `addons/core/`
- Consumer CI: `addons/lighting/`
- Direction: one way. `core` must initialise before `lighting` reads.
- Variables crossing: 8.

A variable named `aee_core_{leaf}` is written as `EGVAR(core,leaf)` by the producer and read as `EGVAR(core,leaf)` or `QEGVAR(core,leaf)` by the consumer.

| Variable | Type | Unit | Range | Update | Evidence (first read) | Purpose (Annex C) |
|---|---|---|---|---|---|---|
| `aee_core_biome` | STRING | code | UNKNOWN | UNKNOWN | `addons/lighting/functions/lighting/fnc_applyWorldLighting.sqf:21` | Koppen biome code (map climate class) |
| `aee_core_currentGusts` | SCALAR | m/s | UNKNOWN | UNKNOWN | `addons/lighting/functions/lighting/fnc_applyWorldLighting.sqf:67` | Gust speed in m/s |
| `aee_core_currentHumidity` | SCALAR | percent | 0..100 | UNKNOWN | `addons/lighting/functions/lighting/fnc_applyWorldLighting.sqf:62` | Relative humidity percent |
| `aee_core_currentMoonAzimuth` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/lighting/functions/astronomy/fnc_calculateSolarRadiation.sqf:99` | UNKNOWN |
| `aee_core_currentSolarFlux` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/lighting/functions/astronomy/fnc_calculateSolarRadiation.sqf:68` | UNKNOWN |
| `aee_core_currentSolarRadiation` | SCALAR | fraction | 0..1 | UNKNOWN | `addons/lighting/functions/astronomy/fnc_calculateSolarRadiation.sqf:69` | Solar radiation factor 0..1 |
| `aee_core_currentSunAzimuth` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/lighting/functions/astronomy/fnc_calculateSolarRadiation.sqf:90` | UNKNOWN |
| `aee_core_currentSunElevation` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/lighting/functions/astronomy/fnc_calculateSolarRadiation.sqf:75` | UNKNOWN |

The default value and the update frequency are the producer's contract. They are set in the producer's CBA settings and recorded in `docs/wiki/annexes/annex-c-variable-reference.qmd`. This document records the boundary and the direction, not a second copy of the variable reference.

Regenerate with `python3 tools/architecture/interface_contracts.py`.
