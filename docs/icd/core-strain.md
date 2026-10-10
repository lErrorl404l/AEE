# ICD: core to strain

- Producer CI: `addons/core/`
- Consumer CI: `addons/strain/`
- Direction: one way. `core` must initialise before `strain` reads.
- Variables crossing: 12.

A variable named `aee_core_{leaf}` is written as `EGVAR(core,leaf)` by the producer and read as `EGVAR(core,leaf)` or `QEGVAR(core,leaf)` by the consumer.

| Variable | Type | Unit | Range | Update | Evidence (first read) | Purpose (Annex C) |
|---|---|---|---|---|---|---|
| `aee_core_coldDangerCategory` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/strain/functions/strain/fnc_calculateColdWeatherPerformance.sqf:42` | Cold danger category |
| `aee_core_currentHypoxiaRisk` | SCALAR | fraction | 0..1 | UNKNOWN | `addons/strain/functions/strain/fnc_applyCrossSensitivity.sqf:64` | Hypoxia risk 0..1 |
| `aee_core_currentTemperature` | SCALAR | degrees C | UNKNOWN | UNKNOWN | `addons/strain/functions/strain/fnc_applyMovementSpeed.sqf:64` | Air temperature in C |
| `aee_core_currentUVIndex` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/strain/functions/strain/fnc_calculateUVIndex.sqf:10` | UV index (core alias) |
| `aee_core_currentWBGT` | SCALAR | degrees C | UNKNOWN | UNKNOWN | `addons/strain/functions/strain/fnc_calculateDehydrationRisk.sqf:49` | Wet bulb globe temperature in C |
| `aee_core_currentWindStr` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/strain/functions/strain/fnc_calculateColdWeatherPerformance.sqf:54` | UNKNOWN |
| `aee_core_dexterityPercent` | SCALAR | fraction | 0..1 | UNKNOWN | `addons/strain/functions/strain/fnc_calculateColdWeatherPerformance.sqf:40` | Manual dexterity 0..1 |
| `aee_core_frostbiteMinutes` | SCALAR | minutes | UNKNOWN | UNKNOWN | `addons/strain/functions/strain/fnc_calculateColdWeatherPerformance.sqf:41` | Time to frostbite in minutes |
| `aee_core_referenceAltitude` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/strain/functions/strain/fnc_calculateUVIndex.sqf:43` | UNKNOWN |
| `aee_core_shooterStability` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/strain/functions/strain/fnc_calculateShooterStability.sqf:60` | UNKNOWN |
| `aee_core_updateInterval` | SCALAR | s | UNKNOWN | UNKNOWN | `addons/strain/functions/strain/fnc_calculateDehydrationRisk.sqf:46` | Update interval in seconds |
| `aee_core_windChillTemp` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/strain/functions/strain/fnc_applyMovementSpeed.sqf:66` | Wind chill temperature |

The default value and the update frequency are the producer's contract. They are set in the producer's CBA settings and recorded in `docs/wiki/annexes/annex-c-variable-reference.qmd`. This document records the boundary and the direction, not a second copy of the variable reference.

Regenerate with `python3 tools/architecture/interface_contracts.py`.
