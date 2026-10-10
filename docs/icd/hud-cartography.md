# ICD: hud to cartography

- Producer CI: `addons/hud/`
- Consumer CI: `addons/cartography/`
- Direction: one way. `hud` must initialise before `cartography` reads.
- Variables crossing: 2.

A variable named `aee_hud_{leaf}` is written as `EGVAR(hud,leaf)` by the producer and read as `EGVAR(hud,leaf)` or `QEGVAR(hud,leaf)` by the consumer.

| Variable | Type | Unit | Range | Update | Evidence (first read) | Purpose (Annex C) |
|---|---|---|---|---|---|---|
| `aee_hud_trackerFix` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/cartography/functions/hud/fnc_gpsUpdate.sqf:51` | UNKNOWN |
| `aee_hud_trackerR95` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/cartography/functions/hud/fnc_gpsUpdate.sqf:53` | UNKNOWN |

The default value and the update frequency are the producer's contract. They are set in the producer's CBA settings and recorded in `docs/wiki/annexes/annex-c-variable-reference.qmd`. This document records the boundary and the direction, not a second copy of the variable reference.

Regenerate with `python3 tools/architecture/interface_contracts.py`.
