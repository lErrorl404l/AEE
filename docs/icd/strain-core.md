# ICD: strain to core

- Producer CI: `addons/strain/`
- Consumer CI: `addons/core/`
- Direction: one way. `strain` must initialise before `core` reads.
- Variables crossing: 2.

A variable named `aee_strain_{leaf}` is written as `EGVAR(strain,leaf)` by the producer and read as `EGVAR(strain,leaf)` or `QEGVAR(strain,leaf)` by the consumer.

| Variable | Type | Unit | Range | Update | Evidence (first read) | Purpose (Annex C) |
|---|---|---|---|---|---|---|
| `aee_strain_fatigueEnabled` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/core/functions/fnc_updateEnvironment.sqf:203` | UNKNOWN |
| `aee_strain_stabilityEnabled` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/core/functions/fnc_updateEnvironment.sqf:212` | UNKNOWN |

The default value and the update frequency are the producer's contract. They are set in the producer's CBA settings and recorded in `docs/wiki/annexes/annex-c-variable-reference.qmd`. This document records the boundary and the direction, not a second copy of the variable reference.

Regenerate with `python3 tools/architecture/interface_contracts.py`.
