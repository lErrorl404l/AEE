# ICD: persistence to mobility

- Producer CI: `addons/persistence/`
- Consumer CI: `addons/mobility/`
- Direction: one way. `persistence` must initialise before `mobility` reads.
- Variables crossing: 2.

A variable named `aee_persistence_{leaf}` is written as `EGVAR(persistence,leaf)` by the producer and read as `EGVAR(persistence,leaf)` or `QEGVAR(persistence,leaf)` by the consumer.

| Variable | Type | Unit | Range | Update | Evidence (first read) | Purpose (Annex C) |
|---|---|---|---|---|---|---|
| `aee_persistence_groundFrostPresent` | BOOL | boolean | 0 or 1 | UNKNOWN | `addons/mobility/functions/fnc_updateGroundState.sqf:65` | Ground frost flag |
| `aee_persistence_slabDensity` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/mobility/functions/fnc_calculateAccretionMass.sqf:39` | UNKNOWN |

The default value and the update frequency are the producer's contract. They are set in the producer's CBA settings and recorded in `docs/wiki/annexes/annex-c-variable-reference.qmd`. This document records the boundary and the direction, not a second copy of the variable reference.

Regenerate with `python3 tools/architecture/interface_contracts.py`.
