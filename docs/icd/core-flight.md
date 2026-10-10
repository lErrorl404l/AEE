# ICD: core to flight

- Producer CI: `addons/core/`
- Consumer CI: `addons/flight/`
- Direction: one way. `core` must initialise before `flight` reads.
- Variables crossing: 8.

A variable named `aee_core_{leaf}` is written as `EGVAR(core,leaf)` by the producer and read as `EGVAR(core,leaf)` or `QEGVAR(core,leaf)` by the consumer.

| Variable | Type | Unit | Range | Update | Evidence (first read) | Purpose (Annex C) |
|---|---|---|---|---|---|---|
| `aee_core_currentAirDensity` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/flight/functions/fnc_applyAirframeLoad.sqf:64` | Air density in kg/m3 |
| `aee_core_currentGusts` | SCALAR | m/s | UNKNOWN | UNKNOWN | `addons/flight/functions/fnc_applyFlightTurbulence.sqf:60` | Gust speed in m/s |
| `aee_core_currentTurbulence` | SCALAR | fraction | 0..1 | UNKNOWN | `addons/flight/functions/fnc_applyFlightTurbulence.sqf:59` | Turbulence 0..1 |
| `aee_core_currentWind` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/flight/functions/fnc_applyFlightTurbulence.sqf:67` | Wind vector |
| `aee_core_currentWindDir` | SCALAR | degrees | UNKNOWN | UNKNOWN | `addons/flight/functions/fnc_applyFlightTurbulence.sqf:65` | Wind direction in degrees |
| `aee_core_enabled` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/flight/functions/fnc_applyAirframeLoad.sqf:41` | Master switch |
| `aee_core_referenceAltitude` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/flight/functions/fnc_calculateHelicopterLift.sqf:22` | UNKNOWN |
| `aee_core_simTime` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/flight/functions/fnc_applyFlightTurbulence.sqf:54` | UNKNOWN |

The default value and the update frequency are the producer's contract. They are set in the producer's CBA settings and recorded in `docs/wiki/annexes/annex-c-variable-reference.qmd`. This document records the boundary and the direction, not a second copy of the variable reference.

Regenerate with `python3 tools/architecture/interface_contracts.py`.
