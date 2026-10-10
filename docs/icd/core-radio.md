# ICD: core to radio

- Producer CI: `addons/core/`
- Consumer CI: `addons/radio/`
- Direction: one way. `core` must initialise before `radio` reads.
- Variables crossing: 5.

A variable named `aee_core_{leaf}` is written as `EGVAR(core,leaf)` by the producer and read as `EGVAR(core,leaf)` or `QEGVAR(core,leaf)` by the consumer.

| Variable | Type | Unit | Range | Update | Evidence (first read) | Purpose (Annex C) |
|---|---|---|---|---|---|---|
| `aee_core_biome` | STRING | code | UNKNOWN | UNKNOWN | `addons/radio/functions/fnc_calculateRadioPropagation.sqf:167` | Koppen biome code (map climate class) |
| `aee_core_currentHumidity` | SCALAR | percent | 0..100 | UNKNOWN | `addons/radio/functions/fnc_calculateRadioPropagation.sqf:30` | Relative humidity percent |
| `aee_core_currentPressure` | SCALAR | hPa | UNKNOWN | UNKNOWN | `addons/radio/functions/fnc_calculateRadioPropagation.sqf:31` | Barometric pressure in hPa |
| `aee_core_currentTemperature` | SCALAR | degrees C | UNKNOWN | UNKNOWN | `addons/radio/functions/fnc_calculateRadioPropagation.sqf:29` | Air temperature in C |
| `aee_core_ionosphericAbsorption` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/radio/functions/fnc_calculateIonosphericAbsorption.sqf:49` | HF absorption in dB |

The default value and the update frequency are the producer's contract. They are set in the producer's CBA settings and recorded in `docs/wiki/annexes/annex-c-variable-reference.qmd`. This document records the boundary and the direction, not a second copy of the variable reference.

Regenerate with `python3 tools/architecture/interface_contracts.py`.
