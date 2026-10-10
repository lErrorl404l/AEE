# ICD: lighting to vision

- Producer CI: `addons/lighting/`
- Consumer CI: `addons/vision/`
- Direction: one way. `lighting` must initialise before `vision` reads.
- Variables crossing: 2.

A variable named `aee_lighting_{leaf}` is written as `EGVAR(lighting,leaf)` by the producer and read as `EGVAR(lighting,leaf)` or `QEGVAR(lighting,leaf)` by the consumer.

| Variable | Type | Unit | Range | Update | Evidence (first read) | Purpose (Annex C) |
|---|---|---|---|---|---|---|
| `aee_lighting_limitingMagnitude` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/vision/functions/vision/fnc_calculateViewDistance.sqf:54` | UNKNOWN |
| `aee_lighting_worldLighting` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/vision/functions/vision/fnc_applyWeatherGrain.sqf:57` | World lighting matcher profile `[nightFactor, starScale, grainScale, hazeScale]` |

The default value and the update frequency are the producer's contract. They are set in the producer's CBA settings and recorded in `docs/wiki/annexes/annex-c-variable-reference.qmd`. This document records the boundary and the direction, not a second copy of the variable reference.

Regenerate with `python3 tools/architecture/interface_contracts.py`.
