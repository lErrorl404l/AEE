# ICD: core to compat_acm

- Producer CI: `addons/core/`
- Consumer CI: `addons/compat_acm/`
- Direction: one way. `core` must initialise before `compat_acm` reads.
- Variables crossing: 2.

A variable named `aee_core_{leaf}` is written as `EGVAR(core,leaf)` by the producer and read as `EGVAR(core,leaf)` or `QEGVAR(core,leaf)` by the consumer.

| Variable | Type | Unit | Range | Update | Evidence (first read) | Purpose (Annex C) |
|---|---|---|---|---|---|---|
| `aee_core_cbrnPersistence` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/compat_acm/functions/fnc_integrateACM.sqf:23` | CBRN persistence 0.225..2.1 |
| `aee_core_currentHypoxiaRisk` | SCALAR | fraction | 0..1 | UNKNOWN | `addons/compat_acm/functions/fnc_registerHypoxiaDutyFactor.sqf:31` | Hypoxia risk 0..1 |

The default value and the update frequency are the producer's contract. They are set in the producer's CBA settings and recorded in `docs/wiki/annexes/annex-c-variable-reference.qmd`. This document records the boundary and the direction, not a second copy of the variable reference.

Regenerate with `python3 tools/architecture/interface_contracts.py`.
