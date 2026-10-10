# ICD: core to optics

- Producer CI: `addons/core/`
- Consumer CI: `addons/optics/`
- Direction: one way. `core` must initialise before `optics` reads.
- Variables crossing: 12.

A variable named `aee_core_{leaf}` is written as `EGVAR(core,leaf)` by the producer and read as `EGVAR(core,leaf)` or `QEGVAR(core,leaf)` by the consumer.

| Variable | Type | Unit | Range | Update | Evidence (first read) | Purpose (Annex C) |
|---|---|---|---|---|---|---|
| `aee_core_biome` | STRING | code | UNKNOWN | UNKNOWN | `addons/optics/functions/sensor/fnc_calculateMirageIntensity.sqf:29` | Koppen biome code (map climate class) |
| `aee_core_currentFogDensity` | SCALAR | fraction | 0..1 | UNKNOWN | `addons/optics/functions/sensor/fnc_calculateAttenuation.sqf:25` | Fog density 0..1 |
| `aee_core_currentHumidity` | SCALAR | percent | 0..100 | UNKNOWN | `addons/optics/functions/sensor/fnc_calculateAtmosphericSeeing.sqf:27` | Relative humidity percent |
| `aee_core_currentTemperature` | SCALAR | degrees C | UNKNOWN | UNKNOWN | `addons/optics/functions/sensor/fnc_calculateAtmosphericSeeing.sqf:26` | Air temperature in C |
| `aee_core_currentTurbulence` | SCALAR | fraction | 0..1 | UNKNOWN | `addons/optics/functions/sensor/fnc_calculateAtmosphericSeeing.sqf:25` | Turbulence 0..1 |
| `aee_core_currentWind` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/optics/functions/sensor/fnc_calculateSmokePersistence.sqf:31` | Wind vector |
| `aee_core_groundState` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/optics/functions/sensor/fnc_calculateAttenuation.sqf:24` | Ground state |
| `aee_core_lightAzimuth` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/optics/functions/sensor/fnc_calculateSolarGlare.sqf:39` | UNKNOWN |
| `aee_core_lightElevation` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/optics/functions/sensor/fnc_calculateSolarGlare.sqf:40` | UNKNOWN |
| `aee_core_opticsEnabled` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/optics/functions/fx/fnc_applyAtmosphericSeeingFX.sqf:8` | UNKNOWN |
| `aee_core_snowDepth_m` | SCALAR | m | UNKNOWN | UNKNOWN | `addons/optics/functions/sensor/fnc_calculatePrecipitationVisibility.sqf:31` | Snow depth in metres |
| `aee_core_updateInterval` | SCALAR | s | UNKNOWN | UNKNOWN | `addons/optics/functions/sensor/fnc_calculateDewOnOptics.sqf:55` | Update interval in seconds |

The default value and the update frequency are the producer's contract. They are set in the producer's CBA settings and recorded in `docs/wiki/annexes/annex-c-variable-reference.qmd`. This document records the boundary and the direction, not a second copy of the variable reference.

Regenerate with `python3 tools/architecture/interface_contracts.py`.
