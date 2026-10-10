# ICD: optics to vision

- Producer CI: `addons/optics/`
- Consumer CI: `addons/vision/`
- Direction: one way. `optics` must initialise before `vision` reads.
- Variables crossing: 14.

A variable named `aee_optics_{leaf}` is written as `EGVAR(optics,leaf)` by the producer and read as `EGVAR(optics,leaf)` or `QEGVAR(optics,leaf)` by the consumer.

| Variable | Type | Unit | Range | Update | Evidence (first read) | Purpose (Annex C) |
|---|---|---|---|---|---|---|
| `aee_optics_chromaCap` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/vision/functions/vision/fnc_managePostProcess.sqf:224` | UNKNOWN |
| `aee_optics_dewBlur` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/vision/functions/vision/fnc_managePostProcess.sqf:212` | Dew blur |
| `aee_optics_dewOnOptics` | SCALAR | fraction | 0..1 | UNKNOWN | `addons/vision/functions/perception/fnc_perceptionUpdate.sqf:180` | Dew on optics 0..1 |
| `aee_optics_glareBlur` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/vision/functions/vision/fnc_managePostProcess.sqf:214` | Glare blur |
| `aee_optics_mirageIntensity` | SCALAR | fraction | 0..1 | UNKNOWN | `addons/vision/functions/perception/fnc_perceptionUpdate.sqf:176` | Mirage intensity 0..1 |
| `aee_optics_rainBlur` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/vision/functions/vision/fnc_managePostProcess.sqf:213` | Rain blur |
| `aee_optics_rainOnOptics` | SCALAR | fraction | 0..1 | UNKNOWN | `addons/vision/functions/perception/fnc_perceptionUpdate.sqf:182` | Rain on optics 0..1 |
| `aee_optics_seeingChroma` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/vision/functions/vision/fnc_managePostProcess.sqf:208` | Seeing chromatic aberration |
| `aee_optics_severeWeatherBlur` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/vision/functions/vision/fnc_managePostProcess.sqf:215` | UNKNOWN |
| `aee_optics_severeWeatherCC` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/vision/functions/vision/fnc_managePostProcess.sqf:220` | UNKNOWN |
| `aee_optics_shimmerChroma` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/vision/functions/vision/fnc_managePostProcess.sqf:209` | Shimmer chromatic aberration |
| `aee_optics_snowBlindness` | SCALAR | fraction | 0..1 | UNKNOWN | `addons/vision/functions/perception/fnc_perceptionUpdate.sqf:178` | Snow blindness 0..1 |
| `aee_optics_snowBlindnessCC` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/vision/functions/vision/fnc_managePostProcess.sqf:221` | UNKNOWN |
| `aee_optics_solarGlareIntensity` | SCALAR | fraction | 0..1 | UNKNOWN | `addons/vision/functions/perception/fnc_perceptionUpdate.sqf:174` | Solar glare 0..1 |

The default value and the update frequency are the producer's contract. They are set in the producer's CBA settings and recorded in `docs/wiki/annexes/annex-c-variable-reference.qmd`. This document records the boundary and the direction, not a second copy of the variable reference.

Regenerate with `python3 tools/architecture/interface_contracts.py`.
