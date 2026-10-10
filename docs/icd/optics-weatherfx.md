# ICD: optics to weatherfx

- Producer CI: `addons/optics/`
- Consumer CI: `addons/weatherfx/`
- Direction: one way. `optics` must initialise before `weatherfx` reads.
- Variables crossing: 2.

A variable named `aee_optics_{leaf}` is written as `EGVAR(optics,leaf)` by the producer and read as `EGVAR(optics,leaf)` or `QEGVAR(optics,leaf)` by the consumer.

| Variable | Type | Unit | Range | Update | Evidence (first read) | Purpose (Annex C) |
|---|---|---|---|---|---|---|
| `aee_optics_severeWeatherBlur` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/weatherfx/functions/weather/fnc_triggerSevereWeatherFX.sqf:11` | UNKNOWN |
| `aee_optics_severeWeatherCC` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/weatherfx/functions/weather/fnc_triggerSevereWeatherFX.sqf:11` | UNKNOWN |

The default value and the update frequency are the producer's contract. They are set in the producer's CBA settings and recorded in `docs/wiki/annexes/annex-c-variable-reference.qmd`. This document records the boundary and the direction, not a second copy of the variable reference.

Regenerate with `python3 tools/architecture/interface_contracts.py`.
