# ICD: core to wildlife

- Producer CI: `addons/core/`
- Consumer CI: `addons/wildlife/`
- Direction: one way. `core` must initialise before `wildlife` reads.
- Variables crossing: 4.

A variable named `aee_core_{leaf}` is written as `EGVAR(core,leaf)` by the producer and read as `EGVAR(core,leaf)` or `QEGVAR(core,leaf)` by the consumer.

| Variable | Type | Unit | Range | Update | Evidence (first read) | Purpose (Annex C) |
|---|---|---|---|---|---|---|
| `aee_core_currentSunElevation` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/wildlife/functions/fnc_spawnFauna.sqf:64` | UNKNOWN |
| `aee_core_currentTemperature` | SCALAR | degrees C | UNKNOWN | UNKNOWN | `addons/wildlife/functions/fnc_applyAnimalBehaviour.sqf:158` | Air temperature in C |
| `aee_core_soilMoisture` | SCALAR | fraction | 0..1 | UNKNOWN | `addons/wildlife/functions/fnc_wildlifeTick.sqf:68` | Soil moisture 0..1 |
| `aee_core_surfaceWetness` | SCALAR | fraction | 0..1 | UNKNOWN | `addons/wildlife/functions/fnc_wildlifeTick.sqf:69` | Surface wetness 0..1 |

The default value and the update frequency are the producer's contract. They are set in the producer's CBA settings and recorded in `docs/wiki/annexes/annex-c-variable-reference.qmd`. This document records the boundary and the direction, not a second copy of the variable reference.

Regenerate with `python3 tools/architecture/interface_contracts.py`.
