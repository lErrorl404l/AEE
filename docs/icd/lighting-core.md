# ICD: lighting to core

- Producer CI: `addons/lighting/`
- Consumer CI: `addons/core/`
- Direction: one way. `lighting` must initialise before `core` reads.
- Variables crossing: 4.

A variable named `aee_lighting_{leaf}` is written as `EGVAR(lighting,leaf)` by the producer and read as `EGVAR(lighting,leaf)` or `QEGVAR(lighting,leaf)` by the consumer.

| Variable | Type | Unit | Range | Update | Evidence (first read) | Purpose (Annex C) |
|---|---|---|---|---|---|---|
| `aee_lighting_ambientBrightness` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/core/functions/fnc_updateEnvironment.sqf:425` | Engine ambient brightness behind the star coefficient (5 s cache) |
| `aee_lighting_houseCache` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/core/functions/fnc_updateEnvironment.sqf:411` | UNKNOWN |
| `aee_lighting_houseCount` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/core/functions/fnc_updateEnvironment.sqf:424` | Nearby house count behind the light-pollution penalty (5 s cache) |
| `aee_lighting_starLightPollutionEnabled` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/core/functions/fnc_updateEnvironment.sqf:418` | UNKNOWN |

The default value and the update frequency are the producer's contract. They are set in the producer's CBA settings and recorded in `docs/wiki/annexes/annex-c-variable-reference.qmd`. This document records the boundary and the direction, not a second copy of the variable reference.

Regenerate with `python3 tools/architecture/interface_contracts.py`.
