# ICD: weather to wildlife

- Producer CI: `addons/weather/`
- Consumer CI: `addons/wildlife/`
- Direction: one way. `weather` must initialise before `wildlife` reads.
- Variables crossing: 3.

A variable named `aee_weather_{leaf}` is written as `EGVAR(weather,leaf)` by the producer and read as `EGVAR(weather,leaf)` or `QEGVAR(weather,leaf)` by the consumer.

| Variable | Type | Unit | Range | Update | Evidence (first read) | Purpose (Annex C) |
|---|---|---|---|---|---|---|
| `aee_weather_currentSoundPropagation` | SCALAR | fraction | 0..1 | UNKNOWN | `addons/wildlife/functions/fnc_ecologyTick.sqf:70` | Sound propagation 0..1 |
| `aee_weather_localBiome` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/wildlife/functions/fnc_spawnFauna.sqf:50` | Biome code of the surface under the player (local detail, not the map class) |
| `aee_weather_terrainSignals` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/wildlife/functions/fnc_applyAnimalBehaviour.sqf:46` | Terrain facts the world lighting matcher reads: water fraction and mean elevation |

The default value and the update frequency are the producer's contract. They are set in the producer's CBA settings and recorded in `docs/wiki/annexes/annex-c-variable-reference.qmd`. This document records the boundary and the direction, not a second copy of the variable reference.

Regenerate with `python3 tools/architecture/interface_contracts.py`.
