# ICD: core to radio

- Producer CI: `addons/core/`
- Consumer CI: `addons/radio/`
- Direction: one way. `core` must initialise before `radio` reads.
- Variables crossing: 5.

A variable named `aee_core_{leaf}` is written as `EGVAR(core,leaf)` by the producer and read as `EGVAR(core,leaf)` or `QEGVAR(core,leaf)` by the consumer.

| Variable | Type | Unit | Range | Update | Evidence (first read) | Purpose (Annex C) |
|---|---|---|---|---|---|---|
| `aee_core_currentSunElevation` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/radio/functions/fnc_calculateIonosphericAbsorption.sqf:53` | UNKNOWN |
| `aee_core_currentTemperature` | SCALAR | degrees C | UNKNOWN | UNKNOWN | `addons/radio/functions/radar/fnc_calculateRadarDetection.sqf:12` | Air temperature in C |
| `aee_core_empRadioFactor` | SCALAR | fraction | 0..1 | UNKNOWN | `addons/radio/functions/fnc_calculateRadioPropagation.sqf:56` | Radio degradation factor now, 0..1 |
| `aee_core_ionosphericAbsorption` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/radio/functions/fnc_calculateIonosphericAbsorption.sqf:78` | HF absorption in dB |
| `aee_core_seaStateBeaufort` | SCALAR | fraction | 0..1 | UNKNOWN | `addons/radio/functions/radar/fnc_calculateRadarDetection.sqf:14` | Sea state 0..12 |

The default value and the update frequency are the producer's contract. They are set in the producer's CBA settings and recorded in `docs/wiki/annexes/annex-c-variable-reference.qmd`. This document records the boundary and the direction, not a second copy of the variable reference.

Regenerate with `python3 tools/architecture/interface_contracts.py`.
