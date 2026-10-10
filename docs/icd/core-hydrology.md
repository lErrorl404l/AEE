# ICD: core to hydrology

- Producer CI: `addons/core/`
- Consumer CI: `addons/hydrology/`
- Direction: one way. `core` must initialise before `hydrology` reads.
- Variables crossing: 6.

A variable named `aee_core_{leaf}` is written as `EGVAR(core,leaf)` by the producer and read as `EGVAR(core,leaf)` or `QEGVAR(core,leaf)` by the consumer.

| Variable | Type | Unit | Range | Update | Evidence (first read) | Purpose (Annex C) |
|---|---|---|---|---|---|---|
| `aee_core_biome` | STRING | code | UNKNOWN | UNKNOWN | `addons/hydrology/functions/fnc_calculateRiverWaterLevel.sqf:17` | Koppen biome code (map climate class) |
| `aee_core_currentFloodRisk` | SCALAR | fraction | 0..1 | UNKNOWN | `addons/hydrology/functions/fnc_calculateRiverWaterLevel.sqf:257` | Flash flood risk 0..1 |
| `aee_core_currentTideOffset_m` | SCALAR | m | UNKNOWN | UNKNOWN | `addons/hydrology/functions/fnc_calculateRiverWaterLevel.sqf:208` | Tide offset in metres |
| `aee_core_currentWaterLevel` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/hydrology/functions/fnc_calculateRiverWaterLevel.sqf:256` | River water level |
| `aee_core_soilMoisture` | SCALAR | fraction | 0..1 | UNKNOWN | `addons/hydrology/functions/fnc_calculateRiverWaterLevel.sqf:92` | Soil moisture 0..1 |
| `aee_core_updateInterval` | SCALAR | s | UNKNOWN | UNKNOWN | `addons/hydrology/functions/fnc_calculateRiverWaterLevel.sqf:68` | Update interval in seconds |

The default value and the update frequency are the producer's contract. They are set in the producer's CBA settings and recorded in `docs/wiki/annexes/annex-c-variable-reference.qmd`. This document records the boundary and the direction, not a second copy of the variable reference.

Regenerate with `python3 tools/architecture/interface_contracts.py`.
