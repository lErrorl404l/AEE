# ICD: eye to vision

- Producer CI: `addons/eye/`
- Consumer CI: `addons/vision/`
- Direction: one way. `eye` must initialise before `vision` reads.
- Variables crossing: 13.

A variable named `aee_eye_{leaf}` is written as `EGVAR(eye,leaf)` by the producer and read as `EGVAR(eye,leaf)` or `QEGVAR(eye,leaf)` by the consumer.

| Variable | Type | Unit | Range | Update | Evidence (first read) | Purpose (Annex C) |
|---|---|---|---|---|---|---|
| `aee_eye_eyeAdaptDirection` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/vision/functions/perception/fnc_perceptionUpdate.sqf:128` | Adaptation direction: -1 dark-adapting, 0 settled, +1 light-adapting |
| `aee_eye_eyeAdaptState` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/vision/functions/perception/fnc_perceptionUpdate.sqf:126` | UNKNOWN |
| `aee_eye_eyeAdaptTargetLux` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/vision/functions/perception/fnc_perceptionUpdate.sqf:127` | Scene illuminance the eye model is adapting toward, lx |
| `aee_eye_eyeAdaptTau` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/vision/functions/perception/fnc_perceptionUpdate.sqf:129` | Effective adaptation time constant of the slowest pool, s |
| `aee_eye_eyeAdaptTimeToAdapt` | SCALAR | percent | 0..100 | UNKNOWN | `addons/vision/functions/perception/fnc_perceptionUpdate.sqf:130` | Time to cover 95 percent of the remaining adaptation, s |
| `aee_eye_eyeAdaptedLux` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/vision/functions/grade/fnc_applyBaseGrade.sqf:189` | Adapted scene illuminance after the eye model, lx |
| `aee_eye_eyeAperture` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/vision/functions/perception/fnc_perceptionUpdate.sqf:94` | Aperture the eye model pinned, higher is wider |
| `aee_eye_eyeMesopic` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/vision/functions/grade/fnc_applyBaseGrade.sqf:190` | CIE 191:2010 photopic fraction, 0 scotopic to 1 photopic |
| `aee_eye_eyePinned` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/vision/functions/vision/fnc_exitThermalSensors.sqf:22` | UNKNOWN |
| `aee_eye_eyePupilMm` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/vision/functions/perception/fnc_perceptionUpdate.sqf:96` | Pupil diameter the eye model carries, mm |
| `aee_eye_eyeRawSunElev` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/vision/functions/perception/fnc_perceptionUpdate.sqf:100` | Sun elevation at the sample, degrees (gates the ambient source) |
| `aee_eye_eyeReflectance` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/vision/functions/perception/fnc_perceptionUpdate.sqf:134` | UNKNOWN |
| `aee_eye_eyeSceneLux` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/vision/functions/perception/fnc_perceptionUpdate.sqf:85` | Scene illuminance the eye model sampled, lx |

The default value and the update frequency are the producer's contract. They are set in the producer's CBA settings and recorded in `docs/wiki/annexes/annex-c-variable-reference.qmd`. This document records the boundary and the direction, not a second copy of the variable reference.

Regenerate with `python3 tools/architecture/interface_contracts.py`.
