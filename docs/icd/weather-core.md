# ICD: weather to core

- Producer CI: `addons/weather/`
- Consumer CI: `addons/core/`
- Direction: one way. `weather` must initialise before `core` reads.
- Variables crossing: 2.

A variable named `aee_weather_{leaf}` is written as `EGVAR(weather,leaf)` by the producer and read as `EGVAR(weather,leaf)` or `QEGVAR(weather,leaf)` by the consumer.

| Variable | Type | Unit | Range | Update | Evidence (first read) | Purpose (Annex C) |
|---|---|---|---|---|---|---|
| `aee_weather_auroraIntensity` | SCALAR | fraction | 0..1 | UNKNOWN | `addons/core/functions/fnc_calculateIlluminance.sqf:144` | Aurora intensity 0..1 |
| `aee_weather_lunarPhase` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/core/functions/fnc_updateEnvironment.sqf:411` | UNKNOWN |

The default value and the update frequency are the producer's contract. They are set in the producer's CBA settings and recorded in `docs/wiki/annexes/annex-c-variable-reference.qmd`. This document records the boundary and the direction, not a second copy of the variable reference.

Regenerate with `python3 tools/architecture/interface_contracts.py`.
