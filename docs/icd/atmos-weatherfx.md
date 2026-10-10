# ICD: atmos to weatherfx

- Producer CI: `addons/atmos/`
- Consumer CI: `addons/weatherfx/`
- Direction: one way. `atmos` must initialise before `weatherfx` reads.
- Variables crossing: 2.

A variable named `aee_atmos_{leaf}` is written as `EGVAR(atmos,leaf)` by the producer and read as `EGVAR(atmos,leaf)` or `QEGVAR(atmos,leaf)` by the consumer.

| Variable | Type | Unit | Range | Update | Evidence (first read) | Purpose (Annex C) |
|---|---|---|---|---|---|---|
| `aee_atmos_currentLightningStrike` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/weatherfx/functions/weather/fnc_calculateLightningStrikeEffects.sqf:12` | UNKNOWN |
| `aee_atmos_lastLightningPos` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/weatherfx/functions/weather/fnc_calculateLightningStrikeEffects.sqf:13` | UNKNOWN |

The default value and the update frequency are the producer's contract. They are set in the producer's CBA settings and recorded in `docs/wiki/annexes/annex-c-variable-reference.qmd`. This document records the boundary and the direction, not a second copy of the variable reference.

Regenerate with `python3 tools/architecture/interface_contracts.py`.
