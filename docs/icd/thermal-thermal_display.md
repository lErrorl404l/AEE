# ICD: thermal to thermal_display

- Producer CI: `addons/thermal/`
- Consumer CI: `addons/thermal_display/`
- Direction: one way. `thermal` must initialise before `thermal_display` reads.
- Variables crossing: 11.

A variable named `aee_thermal_{leaf}` is written as `EGVAR(thermal,leaf)` by the producer and read as `EGVAR(thermal,leaf)` or `QEGVAR(thermal,leaf)` by the consumer.

| Variable | Type | Unit | Range | Update | Evidence (first read) | Purpose (Annex C) |
|---|---|---|---|---|---|---|
| `aee_thermal_activeIR` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/thermal_display/XEH_postInit.sqf:39` | Registered setting under **AEE Thermal > Sensor**: enable the active-IR illuminator (client-local, default off) |
| `aee_thermal_agcFullSpan` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/thermal_display/functions/display/fnc_applyThermalVision.sqf:417` | UNKNOWN |
| `aee_thermal_agcRadMax` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/thermal_display/functions/display/fnc_applyThermalVision.sqf:415` | UNKNOWN |
| `aee_thermal_agcRadMin` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/thermal_display/functions/display/fnc_applyThermalVision.sqf:414` | UNKNOWN |
| `aee_thermal_currentThermalContrast` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/thermal_display/functions/display/fnc_applyThermalVision.sqf:29` | UNKNOWN |
| `aee_thermal_selTemperature` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/thermal_display/functions/fusion/fnc_applyFusionFill.sqf:14` | UNKNOWN |
| `aee_thermal_sweepBudget` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/thermal_display/functions/fusion/fnc_applyFusionOverlay.sqf:388` | UNKNOWN |
| `aee_thermal_thermalBaseChannel` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/thermal_display/functions/display/fnc_applyThermalVision.sqf:107` | UNKNOWN |
| `aee_thermal_thermalDebug` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/thermal_display/functions/display/fnc_applyThermalVision.sqf:501` | UNKNOWN |
| `aee_thermal_thermalPolarity` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/thermal_display/functions/display/fnc_applyThermalVision.sqf:377` | UNKNOWN |
| `aee_thermal_thermalTemporalNoise` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/thermal_display/functions/display/fnc_applyThermalVision.sqf:148` | UNKNOWN |

The default value and the update frequency are the producer's contract. They are set in the producer's CBA settings and recorded in `docs/wiki/annexes/annex-c-variable-reference.qmd`. This document records the boundary and the direction, not a second copy of the variable reference.

Regenerate with `python3 tools/architecture/interface_contracts.py`.
