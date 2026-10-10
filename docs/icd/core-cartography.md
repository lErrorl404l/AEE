# ICD: core to cartography

- Producer CI: `addons/core/`
- Consumer CI: `addons/cartography/`
- Direction: one way. `core` must initialise before `cartography` reads.
- Variables crossing: 10.

A variable named `aee_core_{leaf}` is written as `EGVAR(core,leaf)` by the producer and read as `EGVAR(core,leaf)` or `QEGVAR(core,leaf)` by the consumer.

| Variable | Type | Unit | Range | Update | Evidence (first read) | Purpose (Annex C) |
|---|---|---|---|---|---|---|
| `aee_core_biome` | STRING | code | UNKNOWN | UNKNOWN | `addons/cartography/functions/hud/fnc_mapBiomeColor.sqf:8` | Koppen biome code (map climate class) |
| `aee_core_currentFireRisk` | SCALAR | fraction | 0..1 | UNKNOWN | `addons/cartography/functions/hud/fnc_mapClickQuery.sqf:58` | Fire spread risk 0..1 |
| `aee_core_currentFloodRisk` | SCALAR | fraction | 0..1 | UNKNOWN | `addons/cartography/functions/hud/fnc_mapClickQuery.sqf:57` | Flash flood risk 0..1 |
| `aee_core_currentHypoxiaRisk` | SCALAR | fraction | 0..1 | UNKNOWN | `addons/cartography/functions/hud/fnc_mapClickQuery.sqf:61` | Hypoxia risk 0..1 |
| `aee_core_currentLightningRisk` | SCALAR | fraction | 0..1 | UNKNOWN | `addons/cartography/functions/hud/fnc_mapClickQuery.sqf:59` | Lightning risk 0..1 |
| `aee_core_currentTemperature` | SCALAR | degrees C | UNKNOWN | UNKNOWN | `addons/cartography/functions/hud/fnc_mapClickQuery.sqf:53` | Air temperature in C |
| `aee_core_currentWBGT` | SCALAR | degrees C | UNKNOWN | UNKNOWN | `addons/cartography/functions/hud/fnc_mapClickQuery.sqf:54` | Wet bulb globe temperature in C |
| `aee_core_groundState` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/cartography/functions/hud/fnc_mapClickQuery.sqf:55` | Ground state |
| `aee_core_magneticDeclinationDeg` | SCALAR | degrees | UNKNOWN | UNKNOWN | `addons/cartography/functions/hud/fnc_mapDeclinationRose.sqf:10` | Compass deviation in degrees |
| `aee_core_snowDepth_m` | SCALAR | m | UNKNOWN | UNKNOWN | `addons/cartography/functions/hud/fnc_mapClickQuery.sqf:56` | Snow depth in metres |

The default value and the update frequency are the producer's contract. They are set in the producer's CBA settings and recorded in `docs/wiki/annexes/annex-c-variable-reference.qmd`. This document records the boundary and the direction, not a second copy of the variable reference.

Regenerate with `python3 tools/architecture/interface_contracts.py`.
