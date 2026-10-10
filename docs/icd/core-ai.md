# ICD: core to ai

- Producer CI: `addons/core/`
- Consumer CI: `addons/ai/`
- Direction: one way. `core` must initialise before `ai` reads.
- Variables crossing: 2.

A variable named `aee_core_{leaf}` is written as `EGVAR(core,leaf)` by the producer and read as `EGVAR(core,leaf)` or `QEGVAR(core,leaf)` by the consumer.

| Variable | Type | Unit | Range | Update | Evidence (first read) | Purpose (Annex C) |
|---|---|---|---|---|---|---|
| `aee_core_currentFireRisk` | SCALAR | fraction | 0..1 | UNKNOWN | `addons/ai/functions/fnc_planRoute.sqf:61` | Fire spread risk 0..1 |
| `aee_core_currentLightningRisk` | SCALAR | fraction | 0..1 | UNKNOWN | `addons/ai/functions/fnc_planRoute.sqf:62` | Lightning risk 0..1 |

The default value and the update frequency are the producer's contract. They are set in the producer's CBA settings and recorded in `docs/wiki/annexes/annex-c-variable-reference.qmd`. This document records the boundary and the direction, not a second copy of the variable reference.

Regenerate with `python3 tools/architecture/interface_contracts.py`.
