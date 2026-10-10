# ICD: core to mobility

- Producer CI: `addons/core/`
- Consumer CI: `addons/mobility/`
- Direction: one way. `core` must initialise before `mobility` reads.
- Variables crossing: 13.

A variable named `aee_core_{leaf}` is written as `EGVAR(core,leaf)` by the producer and read as `EGVAR(core,leaf)` or `QEGVAR(core,leaf)` by the consumer.

| Variable | Type | Unit | Range | Update | Evidence (first read) | Purpose (Annex C) |
|---|---|---|---|---|---|---|
| `aee_core_avgGroundTemp` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/mobility/functions/fnc_calculateWetTraction.sqf:49` | UNKNOWN |
| `aee_core_biome` | STRING | code | UNKNOWN | UNKNOWN | `addons/mobility/functions/fnc_updateGroundState.sqf:37` | Koppen biome code (map climate class) |
| `aee_core_currentTemperature` | SCALAR | degrees C | UNKNOWN | UNKNOWN | `addons/mobility/functions/fnc_updateGroundState.sqf:36` | Air temperature in C |
| `aee_core_enabled` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/mobility/functions/fnc_applyAccretionMass.sqf:28` | Master switch |
| `aee_core_frozenDepth_m` | SCALAR | m | UNKNOWN | UNKNOWN | `addons/mobility/functions/fnc_updateGroundState.sqf:75` | Frozen depth in metres |
| `aee_core_groundState` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/mobility/functions/fnc_applyGripLoss.sqf:45` | Ground state |
| `aee_core_mudAccretionEnabled` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/mobility/functions/fnc_calculateMudAccretion.sqf:24` | UNKNOWN |
| `aee_core_precipitationPhase` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/mobility/functions/fnc_calculateWetTraction.sqf:48` | Phase (rain/sleet/snow/freezing_rain) |
| `aee_core_rainAccum` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/mobility/functions/fnc_calculateSoilBearingStrength.sqf:21` | Rain accumulation |
| `aee_core_simTime` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/mobility/functions/fnc_applyRollover.sqf:73` | UNKNOWN |
| `aee_core_snowDepth_m` | SCALAR | m | UNKNOWN | UNKNOWN | `addons/mobility/functions/fnc_applyAccretionMass.sqf:60` | Snow depth in metres |
| `aee_core_surfaceWetness` | SCALAR | fraction | 0..1 | UNKNOWN | `addons/mobility/functions/fnc_applyGripLoss.sqf:43` | Surface wetness 0..1 |
| `aee_core_updateInterval` | SCALAR | s | UNKNOWN | UNKNOWN | `addons/mobility/functions/fnc_calculateMudAccretion.sqf:36` | Update interval in seconds |

The default value and the update frequency are the producer's contract. They are set in the producer's CBA settings and recorded in `docs/wiki/annexes/annex-c-variable-reference.qmd`. This document records the boundary and the direction, not a second copy of the variable reference.

Regenerate with `python3 tools/architecture/interface_contracts.py`.
