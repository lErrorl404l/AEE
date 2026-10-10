# ICD: weather to lighting

- Producer CI: `addons/weather/`
- Consumer CI: `addons/lighting/`
- Direction: one way. `weather` must initialise before `lighting` reads.
- Variables crossing: 4.

A variable named `aee_weather_{leaf}` is written as `EGVAR(weather,leaf)` by the producer and read as `EGVAR(weather,leaf)` or `QEGVAR(weather,leaf)` by the consumer.

| Variable | Type | Unit | Range | Update | Evidence (first read) | Purpose (Annex C) |
|---|---|---|---|---|---|---|
| `aee_weather_auroraIntensity` | SCALAR | fraction | 0..1 | UNKNOWN | `addons/lighting/functions/astronomy/fnc_logSkyState.sqf:77` | Aurora intensity 0..1 |
| `aee_weather_auroraVisibility` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/lighting/functions/astronomy/fnc_updateAurora.sqf:7` | UNKNOWN |
| `aee_weather_kpIndex` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/lighting/functions/astronomy/fnc_logSkyState.sqf:54` | Kp index |
| `aee_weather_terrainSignals` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/lighting/functions/lighting/fnc_applyWorldLighting.sqf:24` | Terrain facts the world lighting matcher reads: water fraction and mean elevation |

The default value and the update frequency are the producer's contract. They are set in the producer's CBA settings and recorded in `docs/wiki/annexes/annex-c-variable-reference.qmd`. This document records the boundary and the direction, not a second copy of the variable reference.

Regenerate with `python3 tools/architecture/interface_contracts.py`.
