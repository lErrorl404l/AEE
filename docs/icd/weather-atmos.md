# ICD: weather to atmos

- Producer CI: `addons/weather/`
- Consumer CI: `addons/atmos/`
- Direction: one way. `weather` must initialise before `atmos` reads.
- Variables crossing: 5.

A variable named `aee_weather_{leaf}` is written as `EGVAR(weather,leaf)` by the producer and read as `EGVAR(weather,leaf)` or `QEGVAR(weather,leaf)` by the consumer.

| Variable | Type | Unit | Range | Update | Evidence (first read) | Purpose (Annex C) |
|---|---|---|---|---|---|---|
| `aee_weather_auroraElevationDeg` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/atmos/functions/fnc_dumpState.sqf:65` | Elevation of the auroral oval's equatorward edge above the observer's horizon, deg (90 when overhead) |
| `aee_weather_flareClass` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/atmos/functions/fnc_dumpState.sqf:63` | GOES class of the current flare (e.g. "M2.4"), "" when none |
| `aee_weather_geomagneticDescription` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/atmos/functions/fnc_dumpState.sqf:59` | Geomagnetic description |
| `aee_weather_solarActivity` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/atmos/functions/fnc_dumpState.sqf:57` | Solar activity |
| `aee_weather_xrayFlux` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/atmos/functions/fnc_dumpState.sqf:61` | GOES 1-8 A solar X-ray flux of the current flare, W/m2 (0 when none) |

The default value and the update frequency are the producer's contract. They are set in the producer's CBA settings and recorded in `docs/wiki/annexes/annex-c-variable-reference.qmd`. This document records the boundary and the direction, not a second copy of the variable reference.

Regenerate with `python3 tools/architecture/interface_contracts.py`.
