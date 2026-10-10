# ICD: thermal_display to vision

- Producer CI: `addons/thermal_display/`
- Consumer CI: `addons/vision/`
- Direction: one way. `thermal_display` must initialise before `vision` reads.
- Variables crossing: 8.

A variable named `aee_thermal_display_{leaf}` is written as `EGVAR(thermal_display,leaf)` by the producer and read as `EGVAR(thermal_display,leaf)` or `QEGVAR(thermal_display,leaf)` by the consumer.

| Variable | Type | Unit | Range | Update | Evidence (first read) | Purpose (Annex C) |
|---|---|---|---|---|---|---|
| `aee_thermal_display_fusionAlwaysOn` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/vision/XEH_postInit.sqf:130` | UNKNOWN |
| `aee_thermal_display_fusionFillReg` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/vision/XEH_postInit.sqf:107` | UNKNOWN |
| `aee_thermal_display_fusionMode` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/vision/XEH_postInit.sqf:133` | UNKNOWN |
| `aee_thermal_display_fusionOverlaySaved` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/vision/XEH_postInit.sqf:108` | UNKNOWN |
| `aee_thermal_display_ppHandle_Thermal_Blur` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/vision/XEH_postInit.sqf:56` | UNKNOWN |
| `aee_thermal_display_ppHandle_Thermal_CC` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/vision/XEH_postInit.sqf:54` | UNKNOWN |
| `aee_thermal_display_ppHandle_Thermal_Grain` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/vision/XEH_postInit.sqf:55` | UNKNOWN |
| `aee_thermal_display_ppHandle_Thermal_Vignette` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/vision/XEH_postInit.sqf:53` | UNKNOWN |

The default value and the update frequency are the producer's contract. They are set in the producer's CBA settings and recorded in `docs/wiki/annexes/annex-c-variable-reference.qmd`. This document records the boundary and the direction, not a second copy of the variable reference.

Regenerate with `python3 tools/architecture/interface_contracts.py`.
