# ICD: diagnostics to core

- Producer CI: `addons/diagnostics/`
- Consumer CI: `addons/core/`
- Direction: one way. `diagnostics` must initialise before `core` reads.
- Variables crossing: 3.

A variable named `aee_diagnostics_{leaf}` is written as `EGVAR(diagnostics,leaf)` by the producer and read as `EGVAR(diagnostics,leaf)` or `QEGVAR(diagnostics,leaf)` by the consumer.

| Variable | Type | Unit | Range | Update | Evidence (first read) | Purpose (Annex C) |
|---|---|---|---|---|---|---|
| `aee_diagnostics_consistencyCheck` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/core/XEH_postInit.sqf:49` | UNKNOWN |
| `aee_diagnostics_consistencyInterval` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/core/XEH_postInit.sqf:50` | 
 |
| `aee_diagnostics_diagnostic` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/core/functions/fnc_updateEnvironment.sqf:488` | UNKNOWN |

The default value and the update frequency are the producer's contract. They are set in the producer's CBA settings and recorded in `docs/wiki/annexes/annex-c-variable-reference.qmd`. This document records the boundary and the direction, not a second copy of the variable reference.

Regenerate with `python3 tools/architecture/interface_contracts.py`.
