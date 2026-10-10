# ICD: core to eye

- Producer CI: `addons/core/`
- Consumer CI: `addons/eye/`
- Direction: one way. `core` must initialise before `eye` reads.
- Variables crossing: 6.

A variable named `aee_core_{leaf}` is written as `EGVAR(core,leaf)` by the producer and read as `EGVAR(core,leaf)` or `QEGVAR(core,leaf)` by the consumer.

| Variable | Type | Unit | Range | Update | Evidence (first read) | Purpose (Annex C) |
|---|---|---|---|---|---|---|
| `aee_core_ambientLux` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/eye/functions/eye/fnc_eyeSampleScene.sqf:34` | UNKNOWN |
| `aee_core_clockJump` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/eye/functions/eye/fnc_updateEyeAdaptation.sqf:89` | UNKNOWN |
| `aee_core_currentSunElevation` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/eye/functions/eye/fnc_eyeSampleScene.sqf:61` | UNKNOWN |
| `aee_core_dynamicLux` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/eye/functions/eye/fnc_eyeSampleScene.sqf:36` | Dynamic lux contribution |
| `aee_core_lightAzimuth` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/eye/functions/eye/fnc_updateEyeAdaptation.sqf:228` | UNKNOWN |
| `aee_core_simTime` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/eye/functions/eye/fnc_updateEyeAdaptation.sqf:67` | UNKNOWN |

The default value and the update frequency are the producer's contract. They are set in the producer's CBA settings and recorded in `docs/wiki/annexes/annex-c-variable-reference.qmd`. This document records the boundary and the direction, not a second copy of the variable reference.

Regenerate with `python3 tools/architecture/interface_contracts.py`.
