# ICD: dive to altitude

- Producer CI: `addons/dive/`
- Consumer CI: `addons/altitude/`
- Direction: one way. `dive` must initialise before `altitude` reads.
- Variables crossing: 2.

A variable named `aee_dive_{leaf}` is written as `EGVAR(dive,leaf)` by the producer and read as `EGVAR(dive,leaf)` or `QEGVAR(dive,leaf)` by the consumer.

| Variable | Type | Unit | Range | Update | Evidence (first read) | Purpose (Annex C) |
|---|---|---|---|---|---|---|
| `aee_dive_diveStates` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/altitude/XEH_postInit.sqf:49` | Per-UID ZH-L16C dive state (issue #118): 16x N2 + 16x He tissue loads, gas mix, depth, DCS accumulator |
| `aee_dive_diveUID` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/altitude/XEH_postInit.sqf:54` | UNKNOWN |

The default value and the update frequency are the producer's contract. They are set in the producer's CBA settings and recorded in `docs/wiki/annexes/annex-c-variable-reference.qmd`. This document records the boundary and the direction, not a second copy of the variable reference.

Regenerate with `python3 tools/architecture/interface_contracts.py`.
