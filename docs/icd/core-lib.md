# ICD: core to lib

- Producer CI: `addons/core/`
- Consumer CI: `addons/lib/`
- Direction: one way. `core` must initialise before `lib` reads.
- Variables crossing: 2.

A variable named `aee_core_{leaf}` is written as `EGVAR(core,leaf)` by the producer and read as `EGVAR(core,leaf)` or `QEGVAR(core,leaf)` by the consumer.

| Variable | Type | Unit | Range | Update | Evidence (first read) | Purpose (Annex C) |
|---|---|---|---|---|---|---|
| `aee_core_positionVerdicts` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/lib/functions/geo/fnc_runGeoConsistency.sqf:135` | Per-invariant consistency verdicts |
| `aee_core_worldLocation` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/lib/functions/fnc_getWorldLocation.sqf:50` | UNKNOWN |

The default value and the update frequency are the producer's contract. They are set in the producer's CBA settings and recorded in `docs/wiki/annexes/annex-c-variable-reference.qmd`. This document records the boundary and the direction, not a second copy of the variable reference.

Regenerate with `python3 tools/architecture/interface_contracts.py`.
