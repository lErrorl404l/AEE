# ICD: core to thermal_display

- Producer CI: `addons/core/`
- Consumer CI: `addons/thermal_display/`
- Direction: one way. `core` must initialise before `thermal_display` reads.
- Variables crossing: 10.

A variable named `aee_core_{leaf}` is written as `EGVAR(core,leaf)` by the producer and read as `EGVAR(core,leaf)` or `QEGVAR(core,leaf)` by the consumer.

| Variable | Type | Unit | Range | Update | Evidence (first read) | Purpose (Annex C) |
|---|---|---|---|---|---|---|
| `aee_core_currentAirDensity` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/thermal_display/functions/fusion/fnc_applyFusionOverlay.sqf:210` | Air density in kg/m3 |
| `aee_core_currentFogDensity` | SCALAR | fraction | 0..1 | UNKNOWN | `addons/thermal_display/functions/display/fnc_applyThermalVision.sqf:222` | Fog density 0..1 |
| `aee_core_currentHumidity` | SCALAR | percent | 0..100 | UNKNOWN | `addons/thermal_display/functions/fusion/fnc_applyFusionOverlay.sqf:204` | Relative humidity percent |
| `aee_core_currentSunElevation` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/thermal_display/functions/fusion/fnc_applyFusionOverlay.sqf:240` | UNKNOWN |
| `aee_core_currentTemperature` | SCALAR | degrees C | UNKNOWN | UNKNOWN | `addons/thermal_display/functions/fusion/fnc_applyFusionOverlay.sqf:200` | Air temperature in C |
| `aee_core_currentWindDir` | SCALAR | degrees | UNKNOWN | UNKNOWN | `addons/thermal_display/functions/hud/fnc_hudTapeInfo.sqf:75` | Wind direction in degrees |
| `aee_core_currentWindStr` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/thermal_display/functions/hud/fnc_hudTapeInfo.sqf:74` | UNKNOWN |
| `aee_core_simTime` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/thermal_display/functions/display/fnc_applyThermalVision.sqf:208` | UNKNOWN |
| `aee_core_surfaceWetness` | SCALAR | fraction | 0..1 | UNKNOWN | `addons/thermal_display/functions/fusion/fnc_applyFusionOverlay.sqf:243` | Surface wetness 0..1 |
| `aee_core_thermalCrossoverActive` | BOOL | boolean | 0 or 1 | UNKNOWN | `addons/thermal_display/functions/display/fnc_applyThermalVision.sqf:32` | Thermal crossover flag |

The default value and the update frequency are the producer's contract. They are set in the producer's CBA settings and recorded in `docs/wiki/annexes/annex-c-variable-reference.qmd`. This document records the boundary and the direction, not a second copy of the variable reference.

Regenerate with `python3 tools/architecture/interface_contracts.py`.
