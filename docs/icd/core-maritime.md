# ICD: core to maritime

- Producer CI: `addons/core/`
- Consumer CI: `addons/maritime/`
- Direction: one way. `core` must initialise before `maritime` reads.
- Variables crossing: 7.

A variable named `aee_core_{leaf}` is written as `EGVAR(core,leaf)` by the producer and read as `EGVAR(core,leaf)` or `QEGVAR(core,leaf)` by the consumer.

| Variable | Type | Unit | Range | Update | Evidence (first read) | Purpose (Annex C) |
|---|---|---|---|---|---|---|
| `aee_core_currentTemperature` | SCALAR | degrees C | UNKNOWN | UNKNOWN | `addons/maritime/functions/fnc_calculateSeaSurfaceTemperature.sqf:33` | Air temperature in C |
| `aee_core_currentTideDescription` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/maritime/functions/fnc_calculateTidalPrediction.sqf:106` | Tide description |
| `aee_core_currentTideOffset_m` | SCALAR | m | UNKNOWN | UNKNOWN | `addons/maritime/functions/fnc_calculateTidalPrediction.sqf:105` | Tide offset in metres |
| `aee_core_currentWind` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/maritime/functions/fnc_calculateSeaState.sqf:7` | Wind vector |
| `aee_core_seaStateBeaufort` | SCALAR | fraction | 0..1 | UNKNOWN | `addons/maritime/functions/fnc_calculateSeaState.sqf:59` | Sea state 0..12 |
| `aee_core_seaStateCurrent` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/maritime/functions/fnc_calculateSeaState.sqf:40` | Smoothed sea state |
| `aee_core_seaStateDescription` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/maritime/functions/fnc_calculateSeaState.sqf:61` | Beaufort label |

The default value and the update frequency are the producer's contract. They are set in the producer's CBA settings and recorded in `docs/wiki/annexes/annex-c-variable-reference.qmd`. This document records the boundary and the direction, not a second copy of the variable reference.

Regenerate with `python3 tools/architecture/interface_contracts.py`.
