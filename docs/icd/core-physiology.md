# ICD: core to physiology

- Producer CI: `addons/core/`
- Consumer CI: `addons/physiology/`
- Direction: one way. `core` must initialise before `physiology` reads.
- Variables crossing: 3.

A variable named `aee_core_{leaf}` is written as `EGVAR(core,leaf)` by the producer and read as `EGVAR(core,leaf)` or `QEGVAR(core,leaf)` by the consumer.

| Variable | Type | Unit | Range | Update | Evidence (first read) | Purpose (Annex C) |
|---|---|---|---|---|---|---|
| `aee_core_currentWBGT` | SCALAR | degrees C | UNKNOWN | UNKNOWN | `addons/physiology/functions/hud/fnc_applyHeatStressHUD.sqf:6` | Wet bulb globe temperature in C |
| `aee_core_physiologyEnabled` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/physiology/functions/hud/fnc_applyHeatStressHUD.sqf:21` | UNKNOWN |
| `aee_core_updateInterval` | SCALAR | s | UNKNOWN | UNKNOWN | `addons/physiology/functions/state/fnc_updateFatigueState.sqf:43` | Update interval in seconds |

The default value and the update frequency are the producer's contract. They are set in the producer's CBA settings and recorded in `docs/wiki/annexes/annex-c-variable-reference.qmd`. This document records the boundary and the direction, not a second copy of the variable reference.

Regenerate with `python3 tools/architecture/interface_contracts.py`.
