# ICD: core to ballistics

- Producer CI: `addons/core/`
- Consumer CI: `addons/ballistics/`
- Direction: one way. `core` must initialise before `ballistics` reads.
- Variables crossing: 7.

A variable named `aee_core_{leaf}` is written as `EGVAR(core,leaf)` by the producer and read as `EGVAR(core,leaf)` or `QEGVAR(core,leaf)` by the consumer.

| Variable | Type | Unit | Range | Update | Evidence (first read) | Purpose (Annex C) |
|---|---|---|---|---|---|---|
| `aee_core_currentAirDensity` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/ballistics/functions/fnc_calculateAirDensity.sqf:23` | Air density in kg/m3 |
| `aee_core_currentHumidity` | SCALAR | percent | 0..100 | UNKNOWN | `addons/ballistics/functions/fnc_calculateAirDensity.sqf:6` | Relative humidity percent |
| `aee_core_currentPressure` | SCALAR | hPa | UNKNOWN | UNKNOWN | `addons/ballistics/functions/fnc_calculateAirDensity.sqf:5` | Barometric pressure in hPa |
| `aee_core_currentSunElevation` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/ballistics/functions/fnc_calculateAmmoTemperature.sqf:52` | UNKNOWN |
| `aee_core_currentTemperature` | SCALAR | degrees C | UNKNOWN | UNKNOWN | `addons/ballistics/functions/fnc_calculateAirDensity.sqf:4` | Air temperature in C |
| `aee_core_currentWind` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/ballistics/functions/fnc_calculateCrosswindBallistics.sqf:46` | Wind vector |
| `aee_core_overcast` | SCALAR | fraction | 0..1 | UNKNOWN | `addons/ballistics/functions/fnc_calculateAmmoTemperature.sqf:54` | Engine overcast 0..1 |

The default value and the update frequency are the producer's contract. They are set in the producer's CBA settings and recorded in `docs/wiki/annexes/annex-c-variable-reference.qmd`. This document records the boundary and the direction, not a second copy of the variable reference.

Regenerate with `python3 tools/architecture/interface_contracts.py`.
