# ICD: physiology to strain

- Producer CI: `addons/physiology/`
- Consumer CI: `addons/strain/`
- Direction: one way. `physiology` must initialise before `strain` reads.
- Variables crossing: 2.

A variable named `aee_physiology_{leaf}` is written as `EGVAR(physiology,leaf)` by the producer and read as `EGVAR(physiology,leaf)` or `QEGVAR(physiology,leaf)` by the consumer.

| Variable | Type | Unit | Range | Update | Evidence (first read) | Purpose (Annex C) |
|---|---|---|---|---|---|---|
| `aee_physiology_fatigueFactor` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/strain/functions/strain/fnc_applyMovementSpeed.sqf:46` | UNKNOWN |
| `aee_physiology_wakefulnessHours` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/strain/functions/strain/fnc_calculateShooterStability.sqf:68` | UNKNOWN |

The default value and the update frequency are the producer's contract. They are set in the producer's CBA settings and recorded in `docs/wiki/annexes/annex-c-variable-reference.qmd`. This document records the boundary and the direction, not a second copy of the variable reference.

Regenerate with `python3 tools/architecture/interface_contracts.py`.
