# ICD: hud to cartography

- Producer CI: `addons/hud/`
- Consumer CI: `addons/cartography/`
- Direction: one way. `hud` must initialise before `cartography` reads.
- Variables crossing: 3.

A variable named `aee_hud_{leaf}` is written as `EGVAR(hud,leaf)` by the producer and read as `EGVAR(hud,leaf)` or `QEGVAR(hud,leaf)` by the consumer.

| Variable | Type | Unit | Range | Update | Evidence (first read) | Purpose (Annex C) |
|---|---|---|---|---|---|---|
| `aee_hud_trackerFix` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/cartography/functions/hud/fnc_gpsUpdate.sqf:57` | The worst fix quality in the group (`none`, `degraded` or `ok`) |
| `aee_hud_trackerOwn` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/cartography/functions/hud/fnc_gpsUpdate.sqf:41` | The player's own GPS solution: [reported position AGL, fix quality, R95 m]; nil with the tracker off |
| `aee_hud_trackerR95` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/cartography/functions/hud/fnc_gpsUpdate.sqf:59` | The largest error radius in the group, metres |

The default value and the update frequency are the producer's contract. They are set in the producer's CBA settings and recorded in `docs/wiki/annexes/annex-c-variable-reference.qmd`. This document records the boundary and the direction, not a second copy of the variable reference.

Regenerate with `python3 tools/architecture/interface_contracts.py`.
