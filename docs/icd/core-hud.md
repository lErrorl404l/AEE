# ICD: core to hud

- Producer CI: `addons/core/`
- Consumer CI: `addons/hud/`
- Direction: one way. `core` must initialise before `hud` reads.
- Variables crossing: 4.

A variable named `aee_core_{leaf}` is written as `EGVAR(core,leaf)` by the producer and read as `EGVAR(core,leaf)` or `QEGVAR(core,leaf)` by the consumer.

| Variable | Type | Unit | Range | Update | Evidence (first read) | Purpose (Annex C) |
|---|---|---|---|---|---|---|
| `aee_core_currentHumidity` | SCALAR | percent | 0..100 | UNKNOWN | `addons/hud/functions/hud/fnc_hudUpdate.sqf:68` | Relative humidity percent |
| `aee_core_currentTemperature` | SCALAR | degrees C | UNKNOWN | UNKNOWN | `addons/hud/functions/hud/fnc_hudUpdate.sqf:67` | Air temperature in C |
| `aee_core_currentWindDir` | SCALAR | degrees | UNKNOWN | UNKNOWN | `addons/hud/functions/hud/fnc_hudUpdate.sqf:70` | Wind direction in degrees |
| `aee_core_currentWindStr` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/hud/functions/hud/fnc_hudUpdate.sqf:69` | UNKNOWN |

The default value and the update frequency are the producer's contract. They are set in the producer's CBA settings and recorded in `docs/wiki/annexes/annex-c-variable-reference.qmd`. This document records the boundary and the direction, not a second copy of the variable reference.

Regenerate with `python3 tools/architecture/interface_contracts.py`.
