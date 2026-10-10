# ICD: core to weather

- Producer CI: `addons/core/`
- Consumer CI: `addons/weather/`
- Direction: one way. `core` must initialise before `weather` reads.
- Variables crossing: 31.

A variable named `aee_core_{leaf}` is written as `EGVAR(core,leaf)` by the producer and read as `EGVAR(core,leaf)` or `QEGVAR(core,leaf)` by the consumer.

| Variable | Type | Unit | Range | Update | Evidence (first read) | Purpose (Annex C) |
|---|---|---|---|---|---|---|
| `aee_core_biome` | STRING | code | UNKNOWN | UNKNOWN | `addons/weather/functions/biome/fnc_getBiome.sqf:30` | Koppen biome code (map climate class) |
| `aee_core_biomeName` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/weather/functions/biome/fnc_getBiome.sqf:31` | Biome display name |
| `aee_core_biomeOverride` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/weather/functions/biome/fnc_updateBiomePosition.sqf:32` | UNKNOWN |
| `aee_core_biomeTransitionRadius` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/weather/functions/biome/fnc_getSmoothedBiome.sqf:33` | UNKNOWN |
| `aee_core_builtDensity` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/weather/functions/terrain/fnc_calculateMicroclimate.sqf:78` | UNKNOWN |
| `aee_core_computeMode` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/weather/functions/biome/fnc_getBiome.sqf:79` | UNKNOWN |
| `aee_core_currentAirDensity` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/weather/functions/warnings/fnc_calculateSevereWeather.sqf:73` | Air density in kg/m3 |
| `aee_core_currentBlowingSnow` | SCALAR | fraction | 0..1 | UNKNOWN | `addons/weather/functions/warnings/fnc_calculateSevereWeather.sqf:17` | Blowing snow 0..1 |
| `aee_core_currentCropDensity` | SCALAR | fraction | 0..1 | UNKNOWN | `addons/weather/functions/terrain/fnc_calculateConcealment.sqf:44` | Crop density 0..1 |
| `aee_core_currentDustDevil` | SCALAR | fraction | 0..1 | UNKNOWN | `addons/weather/functions/warnings/fnc_calculateSevereWeather.sqf:17` | Dust devil activity 0..1 |
| `aee_core_currentHumidity` | SCALAR | percent | 0..100 | UNKNOWN | `addons/weather/functions/climatology/fnc_calculateFogBaseAltitude.sqf:13` | Relative humidity percent |
| `aee_core_currentPressure` | SCALAR | hPa | UNKNOWN | UNKNOWN | `addons/weather/functions/climatology/fnc_calculateQNH.sqf:12` | Barometric pressure in hPa |
| `aee_core_currentSandstorm` | SCALAR | fraction | 0..1 | UNKNOWN | `addons/weather/functions/warnings/fnc_calculateSevereWeather.sqf:17` | Sandstorm intensity 0..1 |
| `aee_core_currentSolarRadiation` | SCALAR | fraction | 0..1 | UNKNOWN | `addons/weather/functions/terrain/fnc_calculateMicroclimate.sqf:91` | Solar radiation factor 0..1 |
| `aee_core_currentTemperature` | SCALAR | degrees C | UNKNOWN | UNKNOWN | `addons/weather/functions/climatology/fnc_calculateFogBaseAltitude.sqf:12` | Air temperature in C |
| `aee_core_currentWaterTemperature` | SCALAR | degrees C | UNKNOWN | UNKNOWN | `addons/weather/functions/terrain/fnc_calculateWaterInfluence.sqf:107` | Water temperature in C |
| `aee_core_currentWind` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/weather/functions/fnc_calculateScentDispersion.sqf:24` | Wind vector |
| `aee_core_currentWindDir` | SCALAR | degrees | UNKNOWN | UNKNOWN | `addons/weather/functions/fnc_calculateScentDispersion.sqf:30` | Wind direction in degrees |
| `aee_core_currentWindStr` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/weather/functions/terrain/fnc_calculateMicroclimate.sqf:107` | UNKNOWN |
| `aee_core_dustSuppression` | SCALAR | fraction | 0..1 | UNKNOWN | `addons/weather/functions/terrain/fnc_calculateDustSuppression.sqf:33` | Dust suppression 0..1 |
| `aee_core_fogBase_m` | SCALAR | m | UNKNOWN | UNKNOWN | `addons/weather/functions/climatology/fnc_calculateFogBaseAltitude.sqf:25` | Fog base altitude in metres |
| `aee_core_groundState` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/weather/functions/fnc_calculateScentDispersion.sqf:35` | Ground state |
| `aee_core_moduleBiomeOverride` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/weather/functions/biome/fnc_getBiome.sqf:27` | EDEN biome override |
| `aee_core_pressureAltitude_m` | SCALAR | m | UNKNOWN | UNKNOWN | `addons/weather/functions/climatology/fnc_calculateQNH.sqf:30` | Pressure altitude in metres |
| `aee_core_qnh` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/weather/functions/climatology/fnc_calculateQNH.sqf:29` | QNH pressure setting |
| `aee_core_snowDepth_m` | SCALAR | m | UNKNOWN | UNKNOWN | `addons/weather/functions/terrain/fnc_calculateConcealment.sqf:46` | Snow depth in metres |
| `aee_core_snowMeltFlux_Wm2` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/weather/functions/terrain/fnc_calculateSnowAccumulation.sqf:71` | UNKNOWN |
| `aee_core_stormOverrideIntensity` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/weather/functions/warnings/fnc_calculateSevereWeather.sqf:27` | UNKNOWN |
| `aee_core_stormOverrideType` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/weather/functions/warnings/fnc_calculateSevereWeather.sqf:23` | UNKNOWN |
| `aee_core_stormOverrideUntil` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/weather/functions/warnings/fnc_calculateSevereWeather.sqf:24` | UNKNOWN |
| `aee_core_updateInterval` | SCALAR | s | UNKNOWN | UNKNOWN | `addons/weather/functions/climatology/fnc_calculateSpaceWeather.sqf:44` | Update interval in seconds |

The default value and the update frequency are the producer's contract. They are set in the producer's CBA settings and recorded in `docs/wiki/annexes/annex-c-variable-reference.qmd`. This document records the boundary and the direction, not a second copy of the variable reference.

Regenerate with `python3 tools/architecture/interface_contracts.py`.
