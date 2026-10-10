# ICD: core to thermal

- Producer CI: `addons/core/`
- Consumer CI: `addons/thermal/`
- Direction: one way. `core` must initialise before `thermal` reads.
- Variables crossing: 43.

A variable named `aee_core_{leaf}` is written as `EGVAR(core,leaf)` by the producer and read as `EGVAR(core,leaf)` or `QEGVAR(core,leaf)` by the consumer.

| Variable | Type | Unit | Range | Update | Evidence (first read) | Purpose (Annex C) |
|---|---|---|---|---|---|---|
| `aee_core_avgGroundTemp` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/thermal/functions/solver/fnc_calculateObjectTemperature.sqf:72` | UNKNOWN |
| `aee_core_avgInfantryTemp` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/thermal/functions/solver/fnc_calculateObjectTemperature.sqf:71` | Average infantry temperature |
| `aee_core_avgVehicleTemp` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/thermal/functions/solver/fnc_calculateObjectTemperature.sqf:70` | Average vehicle temperature |
| `aee_core_builtDensity` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/thermal/functions/environment/fnc_updateTemperature.sqf:151` | UNKNOWN |
| `aee_core_clockJump` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/thermal/functions/solver/fnc_updateThermalAGC.sqf:419` | UNKNOWN |
| `aee_core_clothingInsulation` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/thermal/functions/solver/fnc_calculateObjectTemperature.sqf:92` | UNKNOWN |
| `aee_core_clothingInsulationFactor` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/thermal/functions/surface/fnc_calculateClothingInsulation.sqf:14` | Clothing insulation 0.5..2.0 |
| `aee_core_crossoverTimer` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/thermal/functions/environment/fnc_calculateThermalCrossover.sqf:69` | UNKNOWN |
| `aee_core_currentAirDensity` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/thermal/functions/display/fnc_applySelectionThermal.sqf:253` | Air density in kg/m3 |
| `aee_core_currentFogDensity` | SCALAR | fraction | 0..1 | UNKNOWN | `addons/thermal/functions/display/fnc_applySelectionThermal.sqf:252` | Fog density 0..1 |
| `aee_core_currentFreezingRain` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/thermal/functions/environment/fnc_calculateFreezingRain.sqf:36` | Freezing rain intensity |
| `aee_core_currentHeatIndex` | SCALAR | degrees C | UNKNOWN | UNKNOWN | `addons/thermal/functions/environment/fnc_calculateHeatIndex.sqf:19` | NWS heat index in C |
| `aee_core_currentHumidity` | SCALAR | percent | 0..100 | UNKNOWN | `addons/thermal/functions/display/fnc_applySelectionThermal.sqf:251` | Relative humidity percent |
| `aee_core_currentHypothermiaRisk` | SCALAR | fraction | 0..1 | UNKNOWN | `addons/thermal/functions/environment/fnc_calculateHypothermiaRisk.sqf:45` | Hypothermia risk 0..1 |
| `aee_core_currentIcingSeverity` | SCALAR | fraction | 0..1 | UNKNOWN | `addons/thermal/functions/environment/fnc_calculateFreezingRain.sqf:37` | Airframe icing 0..1 |
| `aee_core_currentMoonAzimuth` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/thermal/functions/display/fnc_applySecondSun.sqf:107` | UNKNOWN |
| `aee_core_currentSolarFlux` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/thermal/functions/display/fnc_applySelectionThermal.sqf:245` | UNKNOWN |
| `aee_core_currentSolarRadiation` | SCALAR | fraction | 0..1 | UNKNOWN | `addons/thermal/functions/display/fnc_applyBuildingThermal.sqf:191` | Solar radiation factor 0..1 |
| `aee_core_currentSunAzimuth` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/thermal/functions/display/fnc_applySecondSun.sqf:104` | UNKNOWN |
| `aee_core_currentSunElevation` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/thermal/functions/display/fnc_applySelectionThermal.sqf:261` | UNKNOWN |
| `aee_core_currentTemperature` | SCALAR | degrees C | UNKNOWN | UNKNOWN | `addons/thermal/functions/display/fnc_applyBuildingThermal.sqf:52` | Air temperature in C |
| `aee_core_currentTemperatureBase` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/thermal/functions/environment/fnc_updateTemperature.sqf:37` | UNKNOWN |
| `aee_core_currentWBGT` | SCALAR | degrees C | UNKNOWN | UNKNOWN | `addons/thermal/functions/environment/fnc_calculateWBGT.sqf:12` | Wet bulb globe temperature in C |
| `aee_core_currentWaterTemperature` | SCALAR | degrees C | UNKNOWN | UNKNOWN | `addons/thermal/functions/display/fnc_applySelectionThermal.sqf:565` | Water temperature in C |
| `aee_core_currentWind` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/thermal/functions/display/fnc_applySelectionThermal.sqf:244` | Wind vector |
| `aee_core_enabled` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/thermal/functions/environment/fnc_calculateGlobeTemperature.sqf:42` | Master switch |
| `aee_core_groundState` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/thermal/functions/environment/fnc_calculateHypothermiaRisk.sqf:21` | Ground state |
| `aee_core_groundSurfaceTemp` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/thermal/functions/ground/fnc_calculateGroundTemperature.sqf:142` | UNKNOWN |
| `aee_core_microclimateRadius` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/thermal/functions/environment/fnc_updateTemperature.sqf:163` | UNKNOWN |
| `aee_core_moduleTempOffset` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/thermal/functions/environment/fnc_updateTemperature.sqf:119` | EDEN temperature offset |
| `aee_core_objectTemperatures` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/thermal/functions/environment/fnc_calculateMRT.sqf:88` | UNKNOWN |
| `aee_core_rainAccum` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/thermal/functions/environment/fnc_calculateHypothermiaRisk.sqf:20` | Rain accumulation |
| `aee_core_referenceAltitude` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/thermal/functions/environment/fnc_calculateFreezingRain.sqf:26` | UNKNOWN |
| `aee_core_simTime` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/thermal/functions/display/fnc_applyEngineThermal.sqf:53` | UNKNOWN |
| `aee_core_snowDepth_m` | SCALAR | m | UNKNOWN | UNKNOWN | `addons/thermal/functions/ground/fnc_calculateGroundNodeStack.sqf:208` | Snow depth in metres |
| `aee_core_snowMeltFlux_Wm2` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/thermal/functions/ground/fnc_calculateGroundNodeStack.sqf:253` | UNKNOWN |
| `aee_core_soilMoisture` | SCALAR | fraction | 0..1 | UNKNOWN | `addons/thermal/functions/ground/fnc_calculateGroundNodeStack.sqf:133` | Soil moisture 0..1 |
| `aee_core_surfaceTemperature` | SCALAR | degrees C | UNKNOWN | UNKNOWN | `addons/thermal/functions/environment/fnc_calculateThermalCrossover.sqf:83` | Surface temperature in C |
| `aee_core_surfaceWetness` | SCALAR | fraction | 0..1 | UNKNOWN | `addons/thermal/functions/display/fnc_applySelectionThermal.sqf:693` | Surface wetness 0..1 |
| `aee_core_tempLapseRate` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/thermal/functions/environment/fnc_updateTemperature.sqf:60` | UNKNOWN |
| `aee_core_thermalCrossoverActive` | BOOL | boolean | 0 or 1 | UNKNOWN | `addons/thermal/functions/environment/fnc_calculateThermalCrossover.sqf:82` | Thermal crossover flag |
| `aee_core_urbanHeatIsland` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/thermal/functions/environment/fnc_updateTemperature.sqf:134` | UNKNOWN |
| `aee_core_waterInfluenceRadius` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/thermal/functions/environment/fnc_updateTemperature.sqf:178` | UNKNOWN |

The default value and the update frequency are the producer's contract. They are set in the producer's CBA settings and recorded in `docs/wiki/annexes/annex-c-variable-reference.qmd`. This document records the boundary and the direction, not a second copy of the variable reference.

Regenerate with `python3 tools/architecture/interface_contracts.py`.
