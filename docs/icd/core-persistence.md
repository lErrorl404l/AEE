# ICD: core to persistence

- Producer CI: `addons/core/`
- Consumer CI: `addons/persistence/`
- Direction: one way. `core` must initialise before `persistence` reads.
- Variables crossing: 28.

A variable named `aee_core_{leaf}` is written as `EGVAR(core,leaf)` by the producer and read as `EGVAR(core,leaf)` or `QEGVAR(core,leaf)` by the consumer.

| Variable | Type | Unit | Range | Update | Evidence (first read) | Purpose (Annex C) |
|---|---|---|---|---|---|---|
| `aee_core_biome` | STRING | code | UNKNOWN | UNKNOWN | `addons/persistence/functions/warnings/fnc_calculateFireSpreadRisk.sqf:43` | Koppen biome code (map climate class) |
| `aee_core_cbrnPersistence` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/persistence/functions/warnings/fnc_calculateCBRNPersistence.sqf:17` | CBRN persistence 0.225..2.1 |
| `aee_core_currentAvalancheRisk` | SCALAR | fraction | 0..1 | UNKNOWN | `addons/persistence/functions/warnings/fnc_calculateAvalancheRisk.sqf:22` | Avalanche risk 0..1 |
| `aee_core_currentCropDensity` | SCALAR | fraction | 0..1 | UNKNOWN | `addons/persistence/functions/warnings/fnc_calculateFireSpreadRisk.sqf:44` | Crop density 0..1 |
| `aee_core_currentFireRisk` | SCALAR | fraction | 0..1 | UNKNOWN | `addons/persistence/functions/warnings/fnc_calculateFireSpreadRisk.sqf:28` | Fire spread risk 0..1 |
| `aee_core_currentHumidity` | SCALAR | percent | 0..100 | UNKNOWN | `addons/persistence/functions/terrain/fnc_calculateSurfaceWetness.sqf:14` | Relative humidity percent |
| `aee_core_currentSolarRadiation` | SCALAR | fraction | 0..1 | UNKNOWN | `addons/persistence/functions/terrain/fnc_updateSoilMoisture.sqf:23` | Solar radiation factor 0..1 |
| `aee_core_currentTemperature` | SCALAR | degrees C | UNKNOWN | UNKNOWN | `addons/persistence/functions/terrain/fnc_calculateFreezeThawCycling.sqf:29` | Air temperature in C |
| `aee_core_currentTideOffset_m` | SCALAR | m | UNKNOWN | UNKNOWN | `addons/persistence/functions/warnings/fnc_calculateFlashFloodRisk.sqf:46` | Tide offset in metres |
| `aee_core_currentWindStr` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/persistence/functions/terrain/fnc_detectGroundFrost.sqf:41` | UNKNOWN |
| `aee_core_freezingDegreeDays` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/persistence/functions/terrain/fnc_calculateFreezeThawCycling.sqf:41` | UNKNOWN |
| `aee_core_frozenDepth_m` | SCALAR | m | UNKNOWN | UNKNOWN | `addons/persistence/functions/terrain/fnc_calculateFreezeThawCycling.sqf:23` | Frozen depth in metres |
| `aee_core_groundState` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/persistence/functions/warnings/fnc_calculateAvalancheRisk.sqf:29` | Ground state |
| `aee_core_groundSurfaceTemp` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/persistence/functions/terrain/fnc_detectGroundFrost.sqf:57` | UNKNOWN |
| `aee_core_overcast` | SCALAR | fraction | 0..1 | UNKNOWN | `addons/persistence/functions/terrain/fnc_calculateFrostOnWindscreens.sqf:38` | Engine overcast 0..1 |
| `aee_core_rainAccum` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/persistence/functions/warnings/fnc_calculateFlashFloodRisk.sqf:25` | Rain accumulation |
| `aee_core_seismicActive` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/persistence/functions/seismic/fnc_calculateSeismicActivity.sqf:42` | UNKNOWN |
| `aee_core_seismicDepth` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/persistence/functions/seismic/fnc_calculateSeismicActivity.sqf:55` | UNKNOWN |
| `aee_core_seismicEpicentre` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/persistence/functions/seismic/fnc_calculateSeismicActivity.sqf:56` | UNKNOWN |
| `aee_core_seismicMagnitude` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/persistence/functions/seismic/fnc_calculateSeismicActivity.sqf:54` | UNKNOWN |
| `aee_core_seismicStart` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/persistence/functions/seismic/fnc_calculateSeismicActivity.sqf:57` | UNKNOWN |
| `aee_core_snowDepth_m` | SCALAR | m | UNKNOWN | UNKNOWN | `addons/persistence/functions/terrain/fnc_calculateFreezeThawCycling.sqf:62` | Snow depth in metres |
| `aee_core_snowfallRate` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/persistence/functions/terrain/fnc_calculateIceLoad.sqf:40` | Snowfall rate |
| `aee_core_soilMoisture` | SCALAR | fraction | 0..1 | UNKNOWN | `addons/persistence/functions/terrain/fnc_updateSoilMoisture.sqf:18` | Soil moisture 0..1 |
| `aee_core_surfaceWetness` | SCALAR | fraction | 0..1 | UNKNOWN | `addons/persistence/functions/terrain/fnc_calculateSurfaceWetness.sqf:12` | Surface wetness 0..1 |
| `aee_core_thawDepth_m` | SCALAR | m | UNKNOWN | UNKNOWN | `addons/persistence/functions/terrain/fnc_calculateFreezeThawCycling.sqf:24` | Thaw depth in metres |
| `aee_core_thawingDegreeDays` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/persistence/functions/terrain/fnc_calculateFreezeThawCycling.sqf:42` | UNKNOWN |
| `aee_core_updateInterval` | SCALAR | s | UNKNOWN | UNKNOWN | `addons/persistence/functions/terrain/fnc_calculateFreezeThawCycling.sqf:37` | Update interval in seconds |

The default value and the update frequency are the producer's contract. They are set in the producer's CBA settings and recorded in `docs/wiki/annexes/annex-c-variable-reference.qmd`. This document records the boundary and the direction, not a second copy of the variable reference.

Regenerate with `python3 tools/architecture/interface_contracts.py`.
