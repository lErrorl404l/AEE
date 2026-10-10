# ICD: vision to optics

- Producer CI: `addons/vision/`
- Consumer CI: `addons/optics/`
- Direction: one way. `vision` must initialise before `optics` reads.
- Variables crossing: 6.

A variable named `aee_vision_{leaf}` is written as `EGVAR(vision,leaf)` by the producer and read as `EGVAR(vision,leaf)` or `QEGVAR(vision,leaf)` by the consumer.

| Variable | Type | Unit | Range | Update | Evidence (first read) | Purpose (Annex C) |
|---|---|---|---|---|---|---|
| `aee_vision_blurActive` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/optics/functions/fnc_dumpState.sqf:37` | UNKNOWN |
| `aee_vision_ccActive` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/optics/functions/fnc_dumpState.sqf:40` | UNKNOWN |
| `aee_vision_chromaActive` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/optics/functions/fnc_dumpState.sqf:34` | UNKNOWN |
| `aee_vision_sensorPFH` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/optics/functions/fnc_dumpState.sqf:49` | UNKNOWN |
| `aee_vision_shadowScene` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/optics/functions/fnc_dumpState.sqf:43` | Scene classifier state for the shadow distance (aee-workshop-copy item 6) |
| `aee_vision_viewDistanceTarget` | SCALAR | m | UNKNOWN | UNKNOWN | `addons/optics/functions/fnc_dumpState.sqf:46` | Vision-driven view distance target in metres (issue #138) |

The default value and the update frequency are the producer's contract. They are set in the producer's CBA settings and recorded in `docs/wiki/annexes/annex-c-variable-reference.qmd`. This document records the boundary and the direction, not a second copy of the variable reference.

Regenerate with `python3 tools/architecture/interface_contracts.py`.
