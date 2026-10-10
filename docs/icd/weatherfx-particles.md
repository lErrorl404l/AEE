# ICD: weatherfx to particles

- Producer CI: `addons/weatherfx/`
- Consumer CI: `addons/particles/`
- Direction: one way. `weatherfx` must initialise before `particles` reads.
- Variables crossing: 5.

A variable named `aee_weatherfx_{leaf}` is written as `EGVAR(weatherfx,leaf)` by the producer and read as `EGVAR(weatherfx,leaf)` or `QEGVAR(weatherfx,leaf)` by the consumer.

| Variable | Type | Unit | Range | Update | Evidence (first read) | Purpose (Annex C) |
|---|---|---|---|---|---|---|
| `aee_weatherfx_breathCondensation` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/particles/functions/fnc_dumpState.sqf:22` | UNKNOWN |
| `aee_weatherfx_exhaustRefraction` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/particles/functions/fnc_dumpState.sqf:28` | UNKNOWN |
| `aee_weatherfx_exhaustSources` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/particles/functions/fnc_dumpState.sqf:16` | UNKNOWN |
| `aee_weatherfx_heatHazeEnabled` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/particles/functions/fnc_dumpState.sqf:36` | Couple the exhaust heat-shimmer alpha and size to the ambient temperature |
| `aee_weatherfx_rainSurfaceDrops` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/particles/functions/fnc_dumpState.sqf:24` | UNKNOWN |

The default value and the update frequency are the producer's contract. They are set in the producer's CBA settings and recorded in `docs/wiki/annexes/annex-c-variable-reference.qmd`. This document records the boundary and the direction, not a second copy of the variable reference.

Regenerate with `python3 tools/architecture/interface_contracts.py`.
