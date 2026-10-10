# ICD: core to diagnostics

- Producer CI: `addons/core/`
- Consumer CI: `addons/diagnostics/`
- Direction: one way. `core` must initialise before `diagnostics` reads.
- Variables crossing: 16.

A variable named `aee_core_{leaf}` is written as `EGVAR(core,leaf)` by the producer and read as `EGVAR(core,leaf)` or `QEGVAR(core,leaf)` by the consumer.

| Variable | Type | Unit | Range | Update | Evidence (first read) | Purpose (Annex C) |
|---|---|---|---|---|---|---|
| `aee_core_ambientLux` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/diagnostics/functions/fnc_dumpState.sqf:39` | UNKNOWN |
| `aee_core_biome` | STRING | code | UNKNOWN | UNKNOWN | `addons/diagnostics/functions/fnc_diagnostic.sqf:7` | Koppen biome code (map climate class) |
| `aee_core_biomeName` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/diagnostics/functions/fnc_diagnostic.sqf:8` | Biome display name |
| `aee_core_currentAirDensity` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/diagnostics/functions/fnc_diagnostic.sqf:3` | Air density in kg/m3 |
| `aee_core_currentHumidity` | SCALAR | percent | 0..100 | UNKNOWN | `addons/diagnostics/functions/fnc_diagnostic.sqf:6` | Relative humidity percent |
| `aee_core_currentPressure` | SCALAR | hPa | UNKNOWN | UNKNOWN | `addons/diagnostics/functions/fnc_diagnostic.sqf:5` | Barometric pressure in hPa |
| `aee_core_currentSunElevation` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/diagnostics/functions/fnc_dumpState.sqf:35` | UNKNOWN |
| `aee_core_currentTemperature` | SCALAR | degrees C | UNKNOWN | UNKNOWN | `addons/diagnostics/functions/fnc_diagnostic.sqf:4` | Air temperature in C |
| `aee_core_illuminanceLux` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/diagnostics/functions/fnc_dumpState.sqf:37` | UNKNOWN |
| `aee_core_isReady` | BOOL | boolean | 0 or 1 | UNKNOWN | `addons/diagnostics/functions/fnc_dumpState.sqf:47` | Core module ready flag |
| `aee_core_lightIsNight` | BOOL | boolean | 0 or 1 | UNKNOWN | `addons/diagnostics/functions/fnc_dumpState.sqf:41` | Night flag |
| `aee_core_moduleHealth` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/diagnostics/functions/fnc_reportModuleHealth.sqf:81` | Runtime module-health report: an array of `[component, preInit, postInit]` per module, read back by the debug index and the P100 probe. The report writes it once, 10 s after core postInit |
| `aee_core_overcast` | SCALAR | fraction | 0..1 | UNKNOWN | `addons/diagnostics/functions/fnc_dumpState.sqf:33` | Engine overcast 0..1 |
| `aee_core_ownershipSentinels` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/diagnostics/functions/fnc_dumpState.sqf:54` | UNKNOWN |
| `aee_core_realWeatherActive` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/diagnostics/functions/fnc_dumpState.sqf:45` | UNKNOWN |
| `aee_core_weatherProgressionSeed` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/diagnostics/functions/fnc_dumpState.sqf:43` | Seeded weather progression |

The default value and the update frequency are the producer's contract. They are set in the producer's CBA settings and recorded in `docs/wiki/annexes/annex-c-variable-reference.qmd`. This document records the boundary and the direction, not a second copy of the variable reference.

Regenerate with `python3 tools/architecture/interface_contracts.py`.
