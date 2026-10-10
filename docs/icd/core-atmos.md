# ICD: core to atmos

- Producer CI: `addons/core/`
- Consumer CI: `addons/atmos/`
- Direction: one way. `core` must initialise before `atmos` reads.
- Variables crossing: 41.

A variable named `aee_core_{leaf}` is written as `EGVAR(core,leaf)` by the producer and read as `EGVAR(core,leaf)` or `QEGVAR(core,leaf)` by the consumer.

| Variable | Type | Unit | Range | Update | Evidence (first read) | Purpose (Annex C) |
|---|---|---|---|---|---|---|
| `aee_core_biome` | STRING | code | UNKNOWN | UNKNOWN | `addons/atmos/functions/state/fnc_updateFog.sqf:23` | Koppen biome code (map climate class) |
| `aee_core_cloudCeiling_m` | SCALAR | m | UNKNOWN | UNKNOWN | `addons/atmos/functions/physics/fnc_calculateCloudCeiling.sqf:42` | Cloud base height in metres |
| `aee_core_currentAirDensity` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/atmos/functions/physics/fnc_calculateOrographicPrecipitation.sqf:45` | Air density in kg/m3 |
| `aee_core_currentFogDensity` | SCALAR | fraction | 0..1 | UNKNOWN | `addons/atmos/functions/state/fnc_updateFog.sqf:17` | Fog density 0..1 |
| `aee_core_currentGusts` | SCALAR | m/s | UNKNOWN | UNKNOWN | `addons/atmos/functions/state/fnc_updateWind.sqf:76` | Gust speed in m/s |
| `aee_core_currentHaze` | SCALAR | fraction | 0..1 | UNKNOWN | `addons/atmos/functions/physics/fnc_calculateHaze.sqf:32` | Haze intensity 0..1 |
| `aee_core_currentHumidity` | SCALAR | percent | 0..100 | UNKNOWN | `addons/atmos/functions/physics/fnc_calculateCloudCeiling.sqf:17` | Relative humidity percent |
| `aee_core_currentLightningRisk` | SCALAR | fraction | 0..1 | UNKNOWN | `addons/atmos/functions/physics/fnc_calculateLightning.sqf:15` | Lightning risk 0..1 |
| `aee_core_currentPressure` | SCALAR | hPa | UNKNOWN | UNKNOWN | `addons/atmos/functions/physics/fnc_calculateOrographicPrecipitation.sqf:55` | Barometric pressure in hPa |
| `aee_core_currentPressureTrend` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/atmos/functions/physics/fnc_calculatePressureTrend.sqf:68` | Pressure trend value |
| `aee_core_currentSolarRadiation` | SCALAR | fraction | 0..1 | UNKNOWN | `addons/atmos/functions/physics/fnc_calculateCloudDevelopment.sqf:40` | Solar radiation factor 0..1 |
| `aee_core_currentSunAzimuth` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/atmos/functions/state/fnc_updateRainbow.sqf:23` | UNKNOWN |
| `aee_core_currentSunElevation` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/atmos/functions/physics/fnc_calculateHalo.sqf:73` | UNKNOWN |
| `aee_core_currentTemperature` | SCALAR | degrees C | UNKNOWN | UNKNOWN | `addons/atmos/functions/physics/fnc_calculateAirframeIcing.sqf:23` | Air temperature in C |
| `aee_core_currentTurbulence` | SCALAR | fraction | 0..1 | UNKNOWN | `addons/atmos/functions/physics/fnc_calculateTurbulence.sqf:15` | Turbulence 0..1 |
| `aee_core_currentWeatherForecast` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/atmos/functions/physics/fnc_calculatePressureTrend.sqf:69` | UNKNOWN |
| `aee_core_currentWind` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/atmos/functions/physics/fnc_calculateOrographicPrecipitation.sqf:65` | Wind vector |
| `aee_core_currentWindDir` | SCALAR | degrees | UNKNOWN | UNKNOWN | `addons/atmos/functions/state/fnc_updateWind.sqf:77` | Wind direction in degrees |
| `aee_core_currentWindStr` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/atmos/functions/state/fnc_updateWind.sqf:78` | UNKNOWN |
| `aee_core_dustSuppression` | SCALAR | fraction | 0..1 | UNKNOWN | `addons/atmos/functions/physics/fnc_calculateHaze.sqf:13` | Dust suppression 0..1 |
| `aee_core_fogForecast` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/atmos/functions/state/fnc_updateFog.sqf:100` | Fog forecast |
| `aee_core_hailActive` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/atmos/functions/physics/fnc_calculatePrecipitationPhase.sqf:87` | Hail gate: convective instability + wet-bulb below freezing aloft (#151) |
| `aee_core_hailEnergy` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/atmos/functions/physics/fnc_calculatePrecipitationPhase.sqf:98` | Hailstone [diameter_m, mass_kg, v_t_ms, energy_j] from the convective proxy (#151) |
| `aee_core_moduleWindMultiplier` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/atmos/functions/state/fnc_updateWind.sqf:24` | EDEN wind multiplier |
| `aee_core_orographicFactor` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/atmos/functions/physics/fnc_calculatePrecipitationPhase.sqf:86` | Precipitation enhancement over terrain: 1.0 base, above over an upslope and below over a downslope. The published upslope form (Smith 1979) |
| `aee_core_precipOrographicEnabled` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/atmos/functions/physics/fnc_calculatePrecipitationPhase.sqf:77` | UNKNOWN |
| `aee_core_precipitationPhase` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/atmos/functions/physics/fnc_calculatePrecipitationPhase.sqf:84` | Phase (rain/sleet/snow/freezing_rain) |
| `aee_core_pressureHistory` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/atmos/functions/physics/fnc_calculatePressureTrend.sqf:34` | UNKNOWN |
| `aee_core_pushedWind` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/atmos/functions/state/fnc_updateWind.sqf:90` | Last wind vector pushed to the engine `wind` command |
| `aee_core_realWeatherActive` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/atmos/functions/state/fnc_updateWeatherFront.sqf:48` | UNKNOWN |
| `aee_core_referenceAltitude` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/atmos/functions/state/fnc_updatePressure.sqf:25` | UNKNOWN |
| `aee_core_snowfallRate` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/atmos/functions/physics/fnc_calculatePrecipitationPhase.sqf:85` | Snowfall rate |
| `aee_core_stormOverrideIntensity` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/atmos/functions/physics/fnc_calculateLightning.sqf:27` | UNKNOWN |
| `aee_core_stormOverrideType` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/atmos/functions/physics/fnc_calculateLightning.sqf:23` | UNKNOWN |
| `aee_core_stormOverrideUntil` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/atmos/functions/physics/fnc_calculateLightning.sqf:24` | UNKNOWN |
| `aee_core_surfaceTemperature` | SCALAR | degrees C | UNKNOWN | UNKNOWN | `addons/atmos/functions/physics/fnc_calculatePrecipitationPhase.sqf:28` | Surface temperature in C |
| `aee_core_tempLapseRate` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/atmos/functions/state/fnc_updatePressure.sqf:36` | UNKNOWN |
| `aee_core_updateInterval` | SCALAR | s | UNKNOWN | UNKNOWN | `addons/atmos/functions/physics/fnc_calculateAirframeIcing.sqf:27` | Update interval in seconds |
| `aee_core_weatherProgression` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/atmos/functions/state/fnc_updateWeatherFront.sqf:50` | UNKNOWN |
| `aee_core_windGustFrequency` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/atmos/functions/state/fnc_updateWind.sqf:18` | UNKNOWN |
| `aee_core_windTerrainInfluence` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/atmos/functions/state/fnc_updateWind.sqf:47` | UNKNOWN |

The default value and the update frequency are the producer's contract. They are set in the producer's CBA settings and recorded in `docs/wiki/annexes/annex-c-variable-reference.qmd`. This document records the boundary and the direction, not a second copy of the variable reference.

Regenerate with `python3 tools/architecture/interface_contracts.py`.
