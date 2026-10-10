# ICD: thermal to optics

- Producer CI: `addons/thermal/`
- Consumer CI: `addons/optics/`
- Direction: one way. `thermal` must initialise before `optics` reads.
- Variables crossing: 2.

A variable named `aee_thermal_{leaf}` is written as `EGVAR(thermal,leaf)` by the producer and read as `EGVAR(thermal,leaf)` or `QEGVAR(thermal,leaf)` by the consumer.

| Variable | Type | Unit | Range | Update | Evidence (first read) | Purpose (Annex C) |
|---|---|---|---|---|---|---|
| `aee_thermal_muzzlePos` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/optics/XEH_postInit.sqf:38` | UNKNOWN |
| `aee_thermal_muzzleTime` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/optics/XEH_postInit.sqf:39` | UNKNOWN |

The default value and the update frequency are the producer's contract. They are set in the producer's CBA settings and recorded in `docs/wiki/annexes/annex-c-variable-reference.qmd`. This document records the boundary and the direction, not a second copy of the variable reference.

Regenerate with `python3 tools/architecture/interface_contracts.py`.
