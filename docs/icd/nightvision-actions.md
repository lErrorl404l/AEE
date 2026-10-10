# ICD: nightvision to actions

- Producer CI: `addons/nightvision/`
- Consumer CI: `addons/actions/`
- Direction: one way. `nightvision` must initialise before `actions` reads.
- Variables crossing: 3.

A variable named `aee_nightvision_{leaf}` is written as `EGVAR(nightvision,leaf)` by the producer and read as `EGVAR(nightvision,leaf)` or `QEGVAR(nightvision,leaf)` by the consumer.

| Variable | Type | Unit | Range | Update | Evidence (first read) | Purpose (Annex C) |
|---|---|---|---|---|---|---|
| `aee_nightvision_dofManualDist` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/actions/XEH_postInit.sqf:41` | UNKNOWN |
| `aee_nightvision_dofMode` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/actions/XEH_postInit.sqf:25` | UNKNOWN |
| `aee_nightvision_dofModeSet` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/actions/functions/fnc_dumpState.sqf:31` | UNKNOWN |

The default value and the update frequency are the producer's contract. They are set in the producer's CBA settings and recorded in `docs/wiki/annexes/annex-c-variable-reference.qmd`. This document records the boundary and the direction, not a second copy of the variable reference.

Regenerate with `python3 tools/architecture/interface_contracts.py`.
