# ICD: core to actions

- Producer CI: `addons/core/`
- Consumer CI: `addons/actions/`
- Direction: one way. `core` must initialise before `actions` reads.
- Variables crossing: 28.

A variable named `aee_core_{leaf}` is written as `EGVAR(core,leaf)` by the producer and read as `EGVAR(core,leaf)` or `QEGVAR(core,leaf)` by the consumer.

| Variable | Type | Unit | Range | Update | Evidence (first read) | Purpose (Annex C) |
|---|---|---|---|---|---|---|
| `aee_core_biome` | STRING | code | UNKNOWN | UNKNOWN | `addons/actions/functions/fnc_calculateWeatherReport.sqf:32` | Koppen biome code (map climate class) |
| `aee_core_coldDangerCategory` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/actions/functions/fnc_calculateWeatherReport.sqf:45` | Cold danger category |
| `aee_core_currentAvalancheRisk` | SCALAR | fraction | 0..1 | UNKNOWN | `addons/actions/functions/fnc_calculateWeatherReport.sqf:51` | Avalanche risk 0..1 |
| `aee_core_currentCropDensity` | SCALAR | fraction | 0..1 | UNKNOWN | `addons/actions/functions/fnc_calculateWeatherReport.sqf:40` | Crop density 0..1 |
| `aee_core_currentFireRisk` | SCALAR | fraction | 0..1 | UNKNOWN | `addons/actions/functions/fnc_calculateWeatherReport.sqf:37` | Fire spread risk 0..1 |
| `aee_core_currentFloodRisk` | SCALAR | fraction | 0..1 | UNKNOWN | `addons/actions/functions/fnc_calculateWeatherReport.sqf:42` | Flash flood risk 0..1 |
| `aee_core_currentHaze` | SCALAR | fraction | 0..1 | UNKNOWN | `addons/actions/functions/fnc_calculateWeatherReport.sqf:66` | Haze intensity 0..1 |
| `aee_core_currentHumidity` | SCALAR | percent | 0..100 | UNKNOWN | `addons/actions/functions/fnc_calculateWeatherReport.sqf:14` | Relative humidity percent |
| `aee_core_currentIcingSeverity` | SCALAR | fraction | 0..1 | UNKNOWN | `addons/actions/functions/fnc_calculateWeatherReport.sqf:55` | Airframe icing 0..1 |
| `aee_core_currentLightningRisk` | SCALAR | fraction | 0..1 | UNKNOWN | `addons/actions/functions/fnc_calculateWeatherReport.sqf:38` | Lightning risk 0..1 |
| `aee_core_currentPressure` | SCALAR | hPa | UNKNOWN | UNKNOWN | `addons/actions/functions/fnc_calculateWeatherReport.sqf:13` | Barometric pressure in hPa |
| `aee_core_currentPressureTrend` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/actions/functions/fnc_openAltimeter.sqf:34` | Pressure trend value |
| `aee_core_currentTemperature` | SCALAR | degrees C | UNKNOWN | UNKNOWN | `addons/actions/functions/fnc_calculateWeatherReport.sqf:12` | Air temperature in C |
| `aee_core_currentTideDescription` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/actions/functions/fnc_calculateWeatherReport.sqf:60` | Tide description |
| `aee_core_currentTideOffset_m` | SCALAR | m | UNKNOWN | UNKNOWN | `addons/actions/functions/fnc_calculateWeatherReport.sqf:61` | Tide offset in metres |
| `aee_core_currentUVIndex` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/actions/functions/fnc_calculateWeatherReport.sqf:39` | UV index (core alias) |
| `aee_core_currentWaterLevel` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/actions/functions/fnc_calculateWeatherReport.sqf:41` | River water level |
| `aee_core_currentWeatherForecast` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/actions/functions/fnc_calculateWeatherReport.sqf:35` | UNKNOWN |
| `aee_core_currentWindDir` | SCALAR | degrees | UNKNOWN | UNKNOWN | `addons/actions/functions/fnc_calculateWeatherReport.sqf:15` | Wind direction in degrees |
| `aee_core_dexterityPercent` | SCALAR | fraction | 0..1 | UNKNOWN | `addons/actions/functions/fnc_calculateWeatherReport.sqf:47` | Manual dexterity 0..1 |
| `aee_core_frostbiteMinutes` | SCALAR | minutes | UNKNOWN | UNKNOWN | `addons/actions/functions/fnc_calculateWeatherReport.sqf:48` | Time to frostbite in minutes |
| `aee_core_groundState` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/actions/functions/fnc_calculateWeatherReport.sqf:36` | Ground state |
| `aee_core_precipitationPhase` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/actions/functions/fnc_calculateWeatherReport.sqf:53` | Phase (rain/sleet/snow/freezing_rain) |
| `aee_core_pressureAltitude_m` | SCALAR | m | UNKNOWN | UNKNOWN | `addons/actions/functions/fnc_calculateWeatherReport.sqf:65` | Pressure altitude in metres |
| `aee_core_qnh` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/actions/functions/fnc_calculateWeatherReport.sqf:64` | QNH pressure setting |
| `aee_core_seaStateBeaufort` | SCALAR | fraction | 0..1 | UNKNOWN | `addons/actions/functions/fnc_calculateWeatherReport.sqf:58` | Sea state 0..12 |
| `aee_core_snowfallRate` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/actions/functions/fnc_calculateWeatherReport.sqf:54` | Snowfall rate |
| `aee_core_windChillTemp` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/actions/functions/fnc_calculateWeatherReport.sqf:46` | Wind chill temperature |

The default value and the update frequency are the producer's contract. They are set in the producer's CBA settings and recorded in `docs/wiki/annexes/annex-c-variable-reference.qmd`. This document records the boundary and the direction, not a second copy of the variable reference.

Regenerate with `python3 tools/architecture/interface_contracts.py`.
