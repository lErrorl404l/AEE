# ICD: core to altitude

- Producer CI: `addons/core/`
- Consumer CI: `addons/altitude/`
- Direction: one way. `core` must initialise before `altitude` reads.
- Variables crossing: 3.

A variable named `aee_core_{leaf}` is written as `EGVAR(core,leaf)` by the producer and read as `EGVAR(core,leaf)` or `QEGVAR(core,leaf)` by the consumer.

| Variable | Type | Unit | Range | Update | Evidence (first read) | Purpose (Annex C) |
|---|---|---|---|---|---|---|
| `aee_core_currentHypoxiaRisk` | SCALAR | fraction | 0..1 | UNKNOWN | `addons/altitude/XEH_postInit.sqf:33` | Hypoxia risk 0..1 |
| `aee_core_currentPressure` | SCALAR | hPa | UNKNOWN | UNKNOWN | `addons/altitude/functions/altitude/fnc_calculateHypoxia.sqf:26` | Barometric pressure in hPa |
| `aee_core_updateInterval` | SCALAR | s | UNKNOWN | UNKNOWN | `addons/altitude/functions/altitude/fnc_calculateAltitudeAcclimatization.sqf:31` | Update interval in seconds |

The default value and the update frequency are the producer's contract. They are set in the producer's CBA settings and recorded in `docs/wiki/annexes/annex-c-variable-reference.qmd`. This document records the boundary and the direction, not a second copy of the variable reference.

Regenerate with `python3 tools/architecture/interface_contracts.py`.
