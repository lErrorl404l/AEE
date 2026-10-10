# ICD: atmos to flight

- Producer CI: `addons/atmos/`
- Consumer CI: `addons/flight/`
- Direction: one way. `atmos` must initialise before `flight` reads.
- Variables crossing: 2.

A variable named `aee_atmos_{leaf}` is written as `EGVAR(atmos,leaf)` by the producer and read as `EGVAR(atmos,leaf)` or `QEGVAR(atmos,leaf)` by the consumer.

| Variable | Type | Unit | Range | Update | Evidence (first read) | Purpose (Annex C) |
|---|---|---|---|---|---|---|
| `aee_atmos_airframeIcing` | SCALAR | fraction | 0..1 | UNKNOWN | `addons/flight/functions/fnc_applyAirframeLoad.sqf:73` | Airframe icing 0..1 |
| `aee_atmos_iceAccretion_kg` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/flight/functions/fnc_applyAirframeLoad.sqf:100` | Ice mass in kg |

The default value and the update frequency are the producer's contract. They are set in the producer's CBA settings and recorded in `docs/wiki/annexes/annex-c-variable-reference.qmd`. This document records the boundary and the direction, not a second copy of the variable reference.

Regenerate with `python3 tools/architecture/interface_contracts.py`.
