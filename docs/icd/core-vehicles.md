# ICD: core to vehicles

- Producer CI: `addons/core/`
- Consumer CI: `addons/vehicles/`
- Direction: one way. `core` must initialise before `vehicles` reads.
- Variables crossing: 2.

A variable named `aee_core_{leaf}` is written as `EGVAR(core,leaf)` by the producer and read as `EGVAR(core,leaf)` or `QEGVAR(core,leaf)` by the consumer.

| Variable | Type | Unit | Range | Update | Evidence (first read) | Purpose (Annex C) |
|---|---|---|---|---|---|---|
| `aee_core_currentAirDensity` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/vehicles/functions/fnc_calculateEnginePower.sqf:55` | Air density in kg/m3 |
| `aee_core_currentTemperature` | SCALAR | degrees C | UNKNOWN | UNKNOWN | `addons/vehicles/functions/fnc_calculateEnginePower.sqf:33` | Air temperature in C |

The default value and the update frequency are the producer's contract. They are set in the producer's CBA settings and recorded in `docs/wiki/annexes/annex-c-variable-reference.qmd`. This document records the boundary and the direction, not a second copy of the variable reference.

Regenerate with `python3 tools/architecture/interface_contracts.py`.
