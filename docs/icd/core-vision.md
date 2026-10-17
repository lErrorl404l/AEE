# ICD: core to vision

- Producer CI: `addons/core/`
- Consumer CI: `addons/vision/`
- Direction: one way. `core` must initialise before `vision` reads.
- Variables crossing: 8.

A variable named `aee_core_{leaf}` is written as `EGVAR(core,leaf)` by the producer and read as `EGVAR(core,leaf)` or `QEGVAR(core,leaf)` by the consumer.

| Variable | Type | Unit | Range | Update | Evidence (first read) | Purpose (Annex C) |
|---|---|---|---|---|---|---|
| `aee_core_currentFogExtinction` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/vision/functions/vision/fnc_calculateViewDistance.sqf:54` | Fog extinction coefficient, per km (Kunkel 1984) |
| `aee_core_currentHaze` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/vision/functions/grade/fnc_applyBaseGrade.sqf:249` | Clear-air (haze) extinction at 550 nm, per km (NOAA UPP RH visibility, sigma = 3.0 / vis) |
| `aee_core_currentMoonElevation` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/vision/functions/grade/fnc_applyBaseGrade.sqf:260` | Topocentric moon altitude, deg (Astronomical Almanac series, lib astroPosition) |
| `aee_core_currentPressure` | SCALAR | hPa | UNKNOWN | UNKNOWN | `addons/vision/functions/grade/fnc_applyBaseGrade.sqf:251` | Barometric pressure in hPa |
| `aee_core_currentSunElevation` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/vision/functions/grade/fnc_applyBaseGrade.sqf:245` | UNKNOWN |
| `aee_core_opticsEnabled` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/vision/functions/vision/fnc_applyWeatherGrain.sqf:37` | UNKNOWN |
| `aee_core_ppHandle_optics_BaseAcuity` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/vision/functions/grade/fnc_applyBaseGrade.sqf:69` | UNKNOWN |
| `aee_core_ppHandle_optics_BaseGrade` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/vision/functions/grade/fnc_applyBaseGrade.sqf:68` | UNKNOWN |

The default value and the update frequency are the producer's contract. They are set in the producer's CBA settings and recorded in `docs/wiki/annexes/annex-c-variable-reference.qmd`. This document records the boundary and the direction, not a second copy of the variable reference.

Regenerate with `python3 tools/architecture/interface_contracts.py`.
