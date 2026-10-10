# ICD: core to nightvision

- Producer CI: `addons/core/`
- Consumer CI: `addons/nightvision/`
- Direction: one way. `core` must initialise before `nightvision` reads.
- Variables crossing: 5.

A variable named `aee_core_{leaf}` is written as `EGVAR(core,leaf)` by the producer and read as `EGVAR(core,leaf)` or `QEGVAR(core,leaf)` by the consumer.

| Variable | Type | Unit | Range | Update | Evidence (first read) | Purpose (Annex C) |
|---|---|---|---|---|---|---|
| `aee_core_currentFogDensity` | SCALAR | fraction | 0..1 | UNKNOWN | `addons/nightvision/functions/fnc_applyNightGrain.sqf:11` | Fog density 0..1 |
| `aee_core_currentTemperature` | SCALAR | degrees C | UNKNOWN | UNKNOWN | `addons/nightvision/functions/fnc_applyNVGTubeModel.sqf:443` | Air temperature in C |
| `aee_core_illuminanceLux` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/nightvision/functions/fnc_applyNVGTubeModel.sqf:484` | UNKNOWN |
| `aee_core_opticsEnabled` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/nightvision/functions/fnc_applyNightGrain.sqf:28` | UNKNOWN |
| `aee_core_simTime` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/nightvision/functions/fnc_applyNVGTubeModel.sqf:598` | UNKNOWN |

The default value and the update frequency are the producer's contract. They are set in the producer's CBA settings and recorded in `docs/wiki/annexes/annex-c-variable-reference.qmd`. This document records the boundary and the direction, not a second copy of the variable reference.

Regenerate with `python3 tools/architecture/interface_contracts.py`.
