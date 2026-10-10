# ICD: nightvision to vision

- Producer CI: `addons/nightvision/`
- Consumer CI: `addons/vision/`
- Direction: one way. `nightvision` must initialise before `vision` reads.
- Variables crossing: 4.

A variable named `aee_nightvision_{leaf}` is written as `EGVAR(nightvision,leaf)` by the producer and read as `EGVAR(nightvision,leaf)` or `QEGVAR(nightvision,leaf)` by the consumer.

| Variable | Type | Unit | Range | Update | Evidence (first read) | Purpose (Annex C) |
|---|---|---|---|---|---|---|
| `aee_nightvision_ppHandle_NVG_Bloom` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/vision/XEH_postInit.sqf:44` | UNKNOWN |
| `aee_nightvision_ppHandle_NVG_CC` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/vision/XEH_postInit.sqf:43` | UNKNOWN |
| `aee_nightvision_ppHandle_NVG_Grain` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/vision/XEH_postInit.sqf:46` | UNKNOWN |
| `aee_nightvision_ppHandle_NVG_Vignette` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/vision/XEH_postInit.sqf:45` | UNKNOWN |

The default value and the update frequency are the producer's contract. They are set in the producer's CBA settings and recorded in `docs/wiki/annexes/annex-c-variable-reference.qmd`. This document records the boundary and the direction, not a second copy of the variable reference.

Regenerate with `python3 tools/architecture/interface_contracts.py`.
