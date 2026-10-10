# ICD: atmos to radio

- Producer CI: `addons/atmos/`
- Consumer CI: `addons/radio/`
- Direction: one way. `atmos` must initialise before `radio` reads.
- Variables crossing: 2.

A variable named `aee_atmos_{leaf}` is written as `EGVAR(atmos,leaf)` by the producer and read as `EGVAR(atmos,leaf)` or `QEGVAR(atmos,leaf)` by the consumer.

| Variable | Type | Unit | Range | Update | Evidence (first read) | Purpose (Annex C) |
|---|---|---|---|---|---|---|
| `aee_atmos_refractionK` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/radio/functions/fnc_calculateRadioPropagation.sqf:63` | K-factor (4/3 earth) |
| `aee_atmos_refractivityGradient` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/radio/functions/radar/fnc_calculateRadarDetection.sqf:11` | Refractivity gradient |

The default value and the update frequency are the producer's contract. They are set in the producer's CBA settings and recorded in `docs/wiki/annexes/annex-c-variable-reference.qmd`. This document records the boundary and the direction, not a second copy of the variable reference.

Regenerate with `python3 tools/architecture/interface_contracts.py`.
