# ICD: weather to radio

- Producer CI: `addons/weather/`
- Consumer CI: `addons/radio/`
- Direction: one way. `weather` must initialise before `radio` reads.
- Variables crossing: 2.

A variable named `aee_weather_{leaf}` is written as `EGVAR(weather,leaf)` by the producer and read as `EGVAR(weather,leaf)` or `QEGVAR(weather,leaf)` by the consumer.

| Variable | Type | Unit | Range | Update | Evidence (first read) | Purpose (Annex C) |
|---|---|---|---|---|---|---|
| `aee_weather_flareHAF` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/radio/functions/fnc_calculateIonosphericAbsorption.sqf:49` | UNKNOWN |
| `aee_weather_sunspotNumber` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/radio/functions/fnc_calculateIonosphericAbsorption.sqf:46` | UNKNOWN |

The default value and the update frequency are the producer's contract. They are set in the producer's CBA settings and recorded in `docs/wiki/annexes/annex-c-variable-reference.qmd`. This document records the boundary and the direction, not a second copy of the variable reference.

Regenerate with `python3 tools/architecture/interface_contracts.py`.
