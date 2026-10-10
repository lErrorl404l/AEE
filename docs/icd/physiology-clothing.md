# ICD: physiology to clothing

- Producer CI: `addons/physiology/`
- Consumer CI: `addons/clothing/`
- Direction: one way. `physiology` must initialise before `clothing` reads.
- Variables crossing: 2.

A variable named `aee_physiology_{leaf}` is written as `EGVAR(physiology,leaf)` by the producer and read as `EGVAR(physiology,leaf)` or `QEGVAR(physiology,leaf)` by the consumer.

| Variable | Type | Unit | Range | Update | Evidence (first read) | Purpose (Annex C) |
|---|---|---|---|---|---|---|
| `aee_physiology_categoryResolvers` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/clothing/functions/clothing/fnc_getItemMass.sqf:460` | UNKNOWN |
| `aee_physiology_massResolvers` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/clothing/functions/clothing/fnc_getInventoryLoad.sqf:50` | UNKNOWN |

The default value and the update frequency are the producer's contract. They are set in the producer's CBA settings and recorded in `docs/wiki/annexes/annex-c-variable-reference.qmd`. This document records the boundary and the direction, not a second copy of the variable reference.

Regenerate with `python3 tools/architecture/interface_contracts.py`.
