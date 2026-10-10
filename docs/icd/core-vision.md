# ICD: core to vision

- Producer CI: `addons/core/`
- Consumer CI: `addons/vision/`
- Direction: one way. `core` must initialise before `vision` reads.
- Variables crossing: 5.

A variable named `aee_core_{leaf}` is written as `EGVAR(core,leaf)` by the producer and read as `EGVAR(core,leaf)` or `QEGVAR(core,leaf)` by the consumer.

| Variable | Type | Unit | Range | Update | Evidence (first read) | Purpose (Annex C) |
|---|---|---|---|---|---|---|
| `aee_core_currentFogDensity` | SCALAR | fraction | 0..1 | UNKNOWN | `addons/vision/functions/vision/fnc_calculateViewDistance.sqf:52` | Fog density 0..1 |
| `aee_core_currentHaze` | SCALAR | fraction | 0..1 | UNKNOWN | `addons/vision/functions/vision/fnc_calculateViewDistance.sqf:53` | Haze intensity 0..1 |
| `aee_core_opticsEnabled` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/vision/functions/vision/fnc_applyWeatherGrain.sqf:35` | UNKNOWN |
| `aee_core_ppHandle_optics_BaseAcuity` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/vision/functions/grade/fnc_applyBaseGrade.sqf:69` | UNKNOWN |
| `aee_core_ppHandle_optics_BaseGrade` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/vision/functions/grade/fnc_applyBaseGrade.sqf:68` | UNKNOWN |

The default value and the update frequency are the producer's contract. They are set in the producer's CBA settings and recorded in `docs/wiki/annexes/annex-c-variable-reference.qmd`. This document records the boundary and the direction, not a second copy of the variable reference.

Regenerate with `python3 tools/architecture/interface_contracts.py`.
