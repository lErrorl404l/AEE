# ICD: eye to optics

- Producer CI: `addons/eye/`
- Consumer CI: `addons/optics/`
- Direction: one way. `eye` must initialise before `optics` reads.
- Variables crossing: 4.

A variable named `aee_eye_{leaf}` is written as `EGVAR(eye,leaf)` by the producer and read as `EGVAR(eye,leaf)` or `QEGVAR(eye,leaf)` by the consumer.

| Variable | Type | Unit | Range | Update | Evidence (first read) | Purpose (Annex C) |
|---|---|---|---|---|---|---|
| `aee_eye_eyeAdaptedLux` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/optics/functions/fnc_dumpState.sqf:25` | Adapted scene illuminance after the eye model, lx |
| `aee_eye_eyeAperture` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/optics/functions/fnc_dumpState.sqf:28` | Aperture the eye model pinned, higher is wider |
| `aee_eye_eyeMesopic` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/optics/functions/fnc_dumpState.sqf:31` | CIE 191:2010 photopic fraction, 0 scotopic to 1 photopic |
| `aee_eye_eyeSceneLux` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/optics/functions/fnc_dumpState.sqf:22` | Scene illuminance the eye model sampled, lx |

The default value and the update frequency are the producer's contract. They are set in the producer's CBA settings and recorded in `docs/wiki/annexes/annex-c-variable-reference.qmd`. This document records the boundary and the direction, not a second copy of the variable reference.

Regenerate with `python3 tools/architecture/interface_contracts.py`.
