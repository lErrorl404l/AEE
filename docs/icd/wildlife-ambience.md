# ICD: wildlife to ambience

- Producer CI: `addons/wildlife/`
- Consumer CI: `addons/ambience/`
- Direction: one way. `wildlife` must initialise before `ambience` reads.
- Variables crossing: 3.

A variable named `aee_wildlife_{leaf}` is written as `EGVAR(wildlife,leaf)` by the producer and read as `EGVAR(wildlife,leaf)` or `QEGVAR(wildlife,leaf)` by the consumer.

| Variable | Type | Unit | Range | Update | Evidence (first read) | Purpose (Annex C) |
|---|---|---|---|---|---|---|
| `aee_wildlife_assetMap` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/ambience/functions/fnc_emitterSync.sqf:40` | The loaded species-to-sound asset map |
| `aee_wildlife_fauna` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/ambience/functions/fnc_emitterSync.sqf:34` | The live fauna list, one entry per spawned animal |
| `aee_wildlife_soundGroup` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/ambience/functions/fnc_emitterSync.sqf:54` | Per-animal asset-map sound group, an object variable |

The default value and the update frequency are the producer's contract. They are set in the producer's CBA settings and recorded in `docs/wiki/annexes/annex-c-variable-reference.qmd`. This document records the boundary and the direction, not a second copy of the variable reference.

Regenerate with `python3 tools/architecture/interface_contracts.py`.
