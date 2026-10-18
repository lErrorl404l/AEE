# Interface Control Documents

Each document defines one boundary between two Configuration Items (CIs). A CI is one addon under `addons/`. A boundary is a variable one CI publishes and another CI reads.

The documents are generated from the source, not from memory. Regenerate with `python3 tools/architecture/interface_contracts.py`. The generator scans every `*.sqf` for `EGVAR(producer,leaf)` and `QEGVAR(producer,leaf)`, the only two cross-addon read forms.

## Naming convention

- File name: `<producer>-<consumer>.md`. The producer is the CI that owns the variable. The consumer is the CI that reads it.
- Variable name: `aee_<producer>_<leaf>`. The producer writes it as `EGVAR(<producer>,<leaf>)`.
- Direction: one way. The producer must initialise before the consumer reads.

## Why this layer exists

JSP 945 controls a Configuration Item and the interface between Configuration Items. The `addons/` tree is the CI decomposition. The interface between two CIs was implicit in the source, so a wiring defect (issue #64) could not be seen from the documentation. This layer makes the boundary explicit and checkable.

## Index

Every boundary with 2 or more crossing variables has its own document. A boundary with one crossing variable is listed in the table below.

| Producer | Consumer | Variables | Document |
|---|---|---|---|
| `core` | `thermal` | 51 | [core-thermal.md](core-thermal.md) |
| `core` | `atmos` | 47 | [core-atmos.md](core-atmos.md) |
| `core` | `weather` | 43 | [core-weather.md](core-weather.md) |
| `core` | `actions` | 28 | [core-actions.md](core-actions.md) |
| `core` | `persistence` | 28 | [core-persistence.md](core-persistence.md) |
| `core` | `optics` | 20 | [core-optics.md](core-optics.md) |
| `core` | `mobility` | 16 | [core-mobility.md](core-mobility.md) |
| `core` | `weatherfx` | 16 | [core-weatherfx.md](core-weatherfx.md) |
| `core` | `diagnostics` | 15 | [core-diagnostics.md](core-diagnostics.md) |
| `optics` | `vision` | 15 | [optics-vision.md](optics-vision.md) |
| `core` | `strain` | 13 | [core-strain.md](core-strain.md) |
| `eye` | `vision` | 13 | [eye-vision.md](eye-vision.md) |
| `core` | `lighting` | 11 | [core-lighting.md](core-lighting.md) |
| `core` | `maritime` | 11 | [core-maritime.md](core-maritime.md) |
| `core` | `particles` | 11 | [core-particles.md](core-particles.md) |
| `core` | `thermal_display` | 11 | [core-thermal_display.md](core-thermal_display.md) |
| `core` | `cartography` | 10 | [core-cartography.md](core-cartography.md) |
| `thermal` | `thermal_display` | 10 | [thermal-thermal_display.md](thermal-thermal_display.md) |
| `core` | `flight` | 9 | [core-flight.md](core-flight.md) |
| `core` | `vision` | 8 | [core-vision.md](core-vision.md) |
| `thermal_display` | `vision` | 8 | [thermal_display-vision.md](thermal_display-vision.md) |
| `core` | `ballistics` | 7 | [core-ballistics.md](core-ballistics.md) |
| `core` | `eye` | 7 | [core-eye.md](core-eye.md) |
| `core` | `hydrology` | 7 | [core-hydrology.md](core-hydrology.md) |
| `thermal_display` | `thermal` | 7 | [thermal_display-thermal.md](thermal_display-thermal.md) |
| `altitude` | `physiology` | 6 | [altitude-physiology.md](altitude-physiology.md) |
| `ambience` | `wildlife` | 6 | [ambience-wildlife.md](ambience-wildlife.md) |
| `core` | `nightvision` | 6 | [core-nightvision.md](core-nightvision.md) |
| `lighting` | `core` | 6 | [lighting-core.md](lighting-core.md) |
| `vision` | `optics` | 6 | [vision-optics.md](vision-optics.md) |
| `core` | `physiology` | 5 | [core-physiology.md](core-physiology.md) |
| `core` | `radio` | 5 | [core-radio.md](core-radio.md) |
| `core` | `vehicles` | 5 | [core-vehicles.md](core-vehicles.md) |
| `nightvision` | `vision` | 5 | [nightvision-vision.md](nightvision-vision.md) |
| `weather` | `atmos` | 5 | [weather-atmos.md](weather-atmos.md) |
| `weatherfx` | `particles` | 5 | [weatherfx-particles.md](weatherfx-particles.md) |
| `ai` | `wildlife` | 4 | [ai-wildlife.md](ai-wildlife.md) |
| `core` | `hud` | 4 | [core-hud.md](core-hud.md) |
| `core` | `wildlife` | 4 | [core-wildlife.md](core-wildlife.md) |
| `eye` | `optics` | 4 | [eye-optics.md](eye-optics.md) |
| `weather` | `lighting` | 4 | [weather-lighting.md](weather-lighting.md) |
| `weather` | `wildlife` | 4 | [weather-wildlife.md](weather-wildlife.md) |
| `core` | `altitude` | 3 | [core-altitude.md](core-altitude.md) |
| `core` | `lib` | 3 | [core-lib.md](core-lib.md) |
| `diagnostics` | `core` | 3 | [diagnostics-core.md](diagnostics-core.md) |
| `hud` | `cartography` | 3 | [hud-cartography.md](hud-cartography.md) |
| `nightvision` | `actions` | 3 | [nightvision-actions.md](nightvision-actions.md) |
| `wildlife` | `ambience` | 3 | [wildlife-ambience.md](wildlife-ambience.md) |
| `atmos` | `flight` | 2 | [atmos-flight.md](atmos-flight.md) |
| `atmos` | `weatherfx` | 2 | [atmos-weatherfx.md](atmos-weatherfx.md) |
| `blast` | `particles` | 2 | [blast-particles.md](blast-particles.md) |
| `core` | `ai` | 2 | [core-ai.md](core-ai.md) |
| `core` | `compat_acm` | 2 | [core-compat_acm.md](core-compat_acm.md) |
| `dive` | `altitude` | 2 | [dive-altitude.md](dive-altitude.md) |
| `magnetism` | `maritime` | 2 | [magnetism-maritime.md](magnetism-maritime.md) |
| `optics` | `weatherfx` | 2 | [optics-weatherfx.md](optics-weatherfx.md) |
| `persistence` | `mobility` | 2 | [persistence-mobility.md](persistence-mobility.md) |
| `physiology` | `clothing` | 2 | [physiology-clothing.md](physiology-clothing.md) |
| `physiology` | `strain` | 2 | [physiology-strain.md](physiology-strain.md) |
| `strain` | `core` | 2 | [strain-core.md](strain-core.md) |
| `symbology` | `hud` | 2 | [symbology-hud.md](symbology-hud.md) |
| `thermal` | `optics` | 2 | [thermal-optics.md](thermal-optics.md) |
| `weather` | `core` | 2 | [weather-core.md](weather-core.md) |
| `weather` | `hud` | 2 | [weather-hud.md](weather-hud.md) |
| `weather` | `radio` | 2 | [weather-radio.md](weather-radio.md) |

## Single-variable boundaries

| Producer | Consumer | Variable |
|---|---|---|
| `atmos` | `optics` | `aee_atmos_refractivityGradient` |
| `atmos` | `persistence` | `aee_atmos_volcanicLaharRisk` |
| `atmos` | `radio` | `aee_atmos_refractivityGradient` |
| `atmos` | `thermal` | `aee_atmos_volcanicWinterRegionalCooling_C` |
| `atmos` | `weather` | `aee_atmos_volcanicAshDepth_mm` |
| `cartography` | `hud` | `aee_cartography_mgrsEnabled` |
| `compat_acm` | `persistence` | `aee_compat_acm_CBRNBasePersistence` |
| `core` | `magnetism` | `aee_core_magneticDeclinationDeg` |
| `diagnostics` | `persistence` | `aee_diagnostics_diagnostic` |
| `diagnostics` | `radio` | `aee_diagnostics_diagnostic` |
| `diagnostics` | `vehicles` | `aee_diagnostics_diagnostic` |
| `diagnostics` | `weather` | `aee_diagnostics_diagnostic` |
| `dive` | `physiology` | `aee_dive_diveStates` |
| `lighting` | `vision` | `aee_lighting_worldLighting` |
| `lighting` | `weatherfx` | `aee_lighting_worldLighting` |
| `ltm` | `nightvision` | `aee_ltm_ltmPFH` |
| `maritime` | `actions` | `aee_maritime_waveHeight_m` |
| `maritime` | `particles` | `aee_maritime_waveHeight_m` |
| `maritime` | `radio` | `aee_maritime_seaSurfaceTemperature` |
| `mobility` | `ai` | `aee_mobility_routePassability` |
| `mobility` | `weatherfx` | `aee_mobility_tractionForce` |
| `nightvision` | `optics` | `aee_nightvision_nvgFlashUntil` |
| `persistence` | `actions` | `aee_persistence_flashFloodRisk` |
| `persistence` | `ai` | `aee_persistence_flashFloodRisk` |
| `persistence` | `thermal` | `aee_persistence_slabDensity` |
| `persistence` | `weather` | `aee_persistence_slabDensity` |
| `physiology` | `ai` | `aee_physiology_survivalPressure` |
| `radio` | `cartography` | `aee_radio_radioPropagationIndex` |
| `radio` | `hud` | `aee_radio_excessLossDB` |
| `strain` | `physiology` | `aee_strain_dehydrationRisk` |
| `symbology` | `cartography` | `aee_symbology_symbologyFont` |
| `thermal` | `nightvision` | `aee_thermal_batteryTemperatureDerating` |
| `thermal` | `radio` | `aee_thermal_batteryTemperatureDerating` |
| `thermal` | `vehicles` | `aee_thermal_batteryTemperatureDerating` |
| `thermal` | `vision` | `aee_thermal_thermalBaseChannel` |
| `vehicles` | `core` | `aee_vehicles_fuelConsumptionEnabled` |
| `vehicles` | `mobility` | `aee_vehicles_vehicleCouplingEnabled` |
| `vision` | `ai` | `aee_vision_viewDistanceTarget` |
| `vision` | `core` | `aee_vision_viewDistanceEnabled` |
| `vision` | `eye` | `aee_vision_illuminantSP` |
| `weather` | `ai` | `aee_weather_currentSoundPropagation` |
| `weather` | `hydrology` | `aee_weather_currentFoliageDensity` |
| `weather` | `thermal` | `aee_weather_terrainSignals` |

Counts: 65 documented boundaries, 43 single-variable boundaries.
