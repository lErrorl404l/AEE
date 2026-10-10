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
| `core` | `thermal` | 43 | [core-thermal.md](core-thermal.md) |
| `core` | `atmos` | 39 | [core-atmos.md](core-atmos.md) |
| `core` | `weather` | 31 | [core-weather.md](core-weather.md) |
| `core` | `actions` | 28 | [core-actions.md](core-actions.md) |
| `core` | `persistence` | 22 | [core-persistence.md](core-persistence.md) |
| `core` | `diagnostics` | 16 | [core-diagnostics.md](core-diagnostics.md) |
| `core` | `weatherfx` | 16 | [core-weatherfx.md](core-weatherfx.md) |
| `optics` | `vision` | 14 | [optics-vision.md](optics-vision.md) |
| `core` | `mobility` | 13 | [core-mobility.md](core-mobility.md) |
| `eye` | `vision` | 13 | [eye-vision.md](eye-vision.md) |
| `core` | `optics` | 12 | [core-optics.md](core-optics.md) |
| `core` | `strain` | 12 | [core-strain.md](core-strain.md) |
| `core` | `particles` | 11 | [core-particles.md](core-particles.md) |
| `thermal` | `thermal_display` | 11 | [thermal-thermal_display.md](thermal-thermal_display.md) |
| `core` | `thermal_display` | 10 | [core-thermal_display.md](core-thermal_display.md) |
| `core` | `flight` | 8 | [core-flight.md](core-flight.md) |
| `core` | `lighting` | 8 | [core-lighting.md](core-lighting.md) |
| `thermal_display` | `vision` | 8 | [thermal_display-vision.md](thermal_display-vision.md) |
| `core` | `ballistics` | 7 | [core-ballistics.md](core-ballistics.md) |
| `core` | `maritime` | 7 | [core-maritime.md](core-maritime.md) |
| `thermal_display` | `thermal` | 7 | [thermal_display-thermal.md](thermal_display-thermal.md) |
| `altitude` | `physiology` | 6 | [altitude-physiology.md](altitude-physiology.md) |
| `ambience` | `wildlife` | 6 | [ambience-wildlife.md](ambience-wildlife.md) |
| `core` | `eye` | 6 | [core-eye.md](core-eye.md) |
| `core` | `hydrology` | 6 | [core-hydrology.md](core-hydrology.md) |
| `vision` | `optics` | 6 | [vision-optics.md](vision-optics.md) |
| `core` | `compat_realweather` | 5 | [core-compat_realweather.md](core-compat_realweather.md) |
| `core` | `nightvision` | 5 | [core-nightvision.md](core-nightvision.md) |
| `core` | `radio` | 5 | [core-radio.md](core-radio.md) |
| `core` | `vision` | 5 | [core-vision.md](core-vision.md) |
| `weatherfx` | `particles` | 5 | [weatherfx-particles.md](weatherfx-particles.md) |
| `ai` | `wildlife` | 4 | [ai-wildlife.md](ai-wildlife.md) |
| `core` | `hud` | 4 | [core-hud.md](core-hud.md) |
| `core` | `wildlife` | 4 | [core-wildlife.md](core-wildlife.md) |
| `eye` | `optics` | 4 | [eye-optics.md](eye-optics.md) |
| `lighting` | `core` | 4 | [lighting-core.md](lighting-core.md) |
| `nightvision` | `vision` | 4 | [nightvision-vision.md](nightvision-vision.md) |
| `weather` | `lighting` | 4 | [weather-lighting.md](weather-lighting.md) |
| `core` | `altitude` | 3 | [core-altitude.md](core-altitude.md) |
| `core` | `physiology` | 3 | [core-physiology.md](core-physiology.md) |
| `diagnostics` | `core` | 3 | [diagnostics-core.md](diagnostics-core.md) |
| `nightvision` | `actions` | 3 | [nightvision-actions.md](nightvision-actions.md) |
| `weather` | `wildlife` | 3 | [weather-wildlife.md](weather-wildlife.md) |
| `wildlife` | `ambience` | 3 | [wildlife-ambience.md](wildlife-ambience.md) |
| `atmos` | `flight` | 2 | [atmos-flight.md](atmos-flight.md) |
| `atmos` | `weatherfx` | 2 | [atmos-weatherfx.md](atmos-weatherfx.md) |
| `blast` | `particles` | 2 | [blast-particles.md](blast-particles.md) |
| `core` | `compat_acm` | 2 | [core-compat_acm.md](core-compat_acm.md) |
| `core` | `lib` | 2 | [core-lib.md](core-lib.md) |
| `core` | `vehicles` | 2 | [core-vehicles.md](core-vehicles.md) |
| `dive` | `altitude` | 2 | [dive-altitude.md](dive-altitude.md) |
| `hud` | `cartography` | 2 | [hud-cartography.md](hud-cartography.md) |
| `lighting` | `vision` | 2 | [lighting-vision.md](lighting-vision.md) |
| `magnetism` | `maritime` | 2 | [magnetism-maritime.md](magnetism-maritime.md) |
| `optics` | `weatherfx` | 2 | [optics-weatherfx.md](optics-weatherfx.md) |
| `persistence` | `mobility` | 2 | [persistence-mobility.md](persistence-mobility.md) |
| `physiology` | `clothing` | 2 | [physiology-clothing.md](physiology-clothing.md) |
| `physiology` | `strain` | 2 | [physiology-strain.md](physiology-strain.md) |
| `strain` | `core` | 2 | [strain-core.md](strain-core.md) |
| `symbology` | `hud` | 2 | [symbology-hud.md](symbology-hud.md) |
| `thermal` | `optics` | 2 | [thermal-optics.md](thermal-optics.md) |
| `weather` | `core` | 2 | [weather-core.md](weather-core.md) |
| `weather` | `radio` | 2 | [weather-radio.md](weather-radio.md) |

## Single-variable boundaries

| Producer | Consumer | Variable |
|---|---|---|
| `atmos` | `radio` | `aee_atmos_refractionK` |
| `cartography` | `hud` | `aee_cartography_mgrsEnabled` |
| `compat_acm` | `persistence` | `aee_compat_acm_CBRNBasePersistence` |
| `core` | `magnetism` | `aee_core_magneticDeclinationDeg` |
| `diagnostics` | `persistence` | `aee_diagnostics_diagnostic` |
| `diagnostics` | `radio` | `aee_diagnostics_diagnostic` |
| `diagnostics` | `vehicles` | `aee_diagnostics_diagnostic` |
| `diagnostics` | `weather` | `aee_diagnostics_diagnostic` |
| `dive` | `physiology` | `aee_dive_diveStates` |
| `lighting` | `weatherfx` | `aee_lighting_worldLighting` |
| `ltm` | `nightvision` | `aee_ltm_ltmPFH` |
| `maritime` | `actions` | `aee_maritime_waveHeight_m` |
| `maritime` | `particles` | `aee_maritime_waveHeight_m` |
| `maritime` | `radio` | `aee_maritime_seaSurfaceTemperature` |
| `mobility` | `weatherfx` | `aee_mobility_tractionForce` |
| `nightvision` | `optics` | `aee_nightvision_nvgFlashUntil` |
| `optics` | `core` | `aee_optics_atmosphericSeeing` |
| `persistence` | `actions` | `aee_persistence_flashFloodRisk` |
| `persistence` | `thermal` | `aee_persistence_slabDensity` |
| `persistence` | `weather` | `aee_persistence_slabDensity` |
| `strain` | `physiology` | `aee_strain_dehydrationRisk` |
| `symbology` | `cartography` | `aee_symbology_symbologyFont` |
| `thermal` | `nightvision` | `aee_thermal_batteryTemperatureDerating` |
| `thermal` | `radio` | `aee_thermal_batteryTemperatureDerating` |
| `thermal` | `vehicles` | `aee_thermal_batteryTemperatureDerating` |
| `thermal` | `vision` | `aee_thermal_thermalBaseChannel` |
| `vehicles` | `mobility` | `aee_vehicles_vehicleCouplingEnabled` |
| `vision` | `core` | `aee_vision_viewDistanceEnabled` |
| `weather` | `thermal` | `aee_weather_terrainSignals` |

Counts: 63 documented boundaries, 29 single-variable boundaries.
