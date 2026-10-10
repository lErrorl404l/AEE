# ICD: magnetism to maritime

- Producer CI: `addons/magnetism/`
- Consumer CI: `addons/maritime/`
- Direction: one way. `magnetism` must initialise before `maritime` reads.
- Variables crossing: 2.

A variable named `aee_magnetism_{leaf}` is written as `EGVAR(magnetism,leaf)` by the producer and read as `EGVAR(magnetism,leaf)` or `QEGVAR(magnetism,leaf)` by the consumer.

| Variable | Type | Unit | Range | Update | Evidence (first read) | Purpose (Annex C) |
|---|---|---|---|---|---|---|
| `aee_magnetism_compassAnomalyNT` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/maritime/functions/fnc_dumpState.sqf:26` | Local ferrous magnetic anomaly in nanotesla: a component of the compass deviation |
| `aee_magnetism_compassDeviation` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/maritime/functions/fnc_dumpState.sqf:24` | Compass deviation (magnetism namespace) |

The default value and the update frequency are the producer's contract. They are set in the producer's CBA settings and recorded in `docs/wiki/annexes/annex-c-variable-reference.qmd`. This document records the boundary and the direction, not a second copy of the variable reference.

Regenerate with `python3 tools/architecture/interface_contracts.py`.
