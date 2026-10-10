# ICD: altitude to physiology

- Producer CI: `addons/altitude/`
- Consumer CI: `addons/physiology/`
- Direction: one way. `altitude` must initialise before `physiology` reads.
- Variables crossing: 6.

A variable named `aee_altitude_{leaf}` is written as `EGVAR(altitude,leaf)` by the producer and read as `EGVAR(altitude,leaf)` or `QEGVAR(altitude,leaf)` by the consumer.

| Variable | Type | Unit | Range | Update | Evidence (first read) | Purpose (Annex C) |
|---|---|---|---|---|---|---|
| `aee_altitude_acclimatizationPercent` | SCALAR | fraction | 0..1 | UNKNOWN | `addons/physiology/XEH_postInit.sqf:11` | Altitude acclimatisation 0..100 |
| `aee_altitude_altitudeState` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/physiology/functions/fnc_dumpState.sqf:30` | UNKNOWN |
| `aee_altitude_gLoad` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/physiology/functions/fnc_dumpState.sqf:16` | Measured Gz load (1 = standing) |
| `aee_altitude_gLocStage` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/physiology/functions/fnc_dumpState.sqf:18` | G-LOC stage 0 none / 1 greyout / 2 blackout / 3 LOC |
| `aee_altitude_hypoxiaExposure` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/physiology/functions/fnc_dumpState.sqf:34` | UNKNOWN |
| `aee_altitude_oxygenState` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/physiology/functions/fnc_dumpState.sqf:32` | UNKNOWN |

The default value and the update frequency are the producer's contract. They are set in the producer's CBA settings and recorded in `docs/wiki/annexes/annex-c-variable-reference.qmd`. This document records the boundary and the direction, not a second copy of the variable reference.

Regenerate with `python3 tools/architecture/interface_contracts.py`.
