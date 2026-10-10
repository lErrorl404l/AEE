# ICD: thermal_display to thermal

- Producer CI: `addons/thermal_display/`
- Consumer CI: `addons/thermal/`
- Direction: one way. `thermal_display` must initialise before `thermal` reads.
- Variables crossing: 7.

A variable named `aee_thermal_display_{leaf}` is written as `EGVAR(thermal_display,leaf)` by the producer and read as `EGVAR(thermal_display,leaf)` or `QEGVAR(thermal_display,leaf)` by the consumer.

| Variable | Type | Unit | Range | Update | Evidence (first read) | Purpose (Annex C) |
|---|---|---|---|---|---|---|
| `aee_thermal_display_bloom` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/thermal/functions/fnc_dumpState.sqf:32` | UNKNOWN |
| `aee_thermal_display_fusionMode` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/thermal/functions/fnc_dumpState.sqf:22` | UNKNOWN |
| `aee_thermal_display_hudTapeOn` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/thermal/functions/fnc_dumpState.sqf:26` | UNKNOWN |
| `aee_thermal_display_outlineOn` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/thermal/functions/fnc_dumpState.sqf:24` | UNKNOWN |
| `aee_thermal_display_repaintHz` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/thermal/functions/display/fnc_applySelectionThermal.sqf:142` | UNKNOWN |
| `aee_thermal_display_thermalActive` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/thermal/functions/fnc_dumpState.sqf:14` | UNKNOWN |
| `aee_thermal_display_thermalFPN` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/thermal/functions/display/fnc_applySelectionThermal.sqf:206` | UNKNOWN |

The default value and the update frequency are the producer's contract. They are set in the producer's CBA settings and recorded in `docs/wiki/annexes/annex-c-variable-reference.qmd`. This document records the boundary and the direction, not a second copy of the variable reference.

Regenerate with `python3 tools/architecture/interface_contracts.py`.
