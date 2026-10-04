# ADR-006: AEE Owns the Human Eye Adaptation Rate

Status: Accepted
Date: 2026-10-04
Decision: AEE computes the adapted scene luminance each frame and pins the camera aperture with `setApertureNew [v, v, v, 1]`. The engine no longer owns the eye adaptation rate.

## Context

The engine can be told an aperture range with `setApertureNew [minimum, standard, maximum, luminance]`, and it then adapts inside that range at its own rate. That rate is not human, and the operator reported that the eye adapts too fast.

The retirement of `addons/atmos/functions/state/fnc_updateAperture.sqf` (issue #141) moved aperture ownership into `addons/optics`. The old bridge handed the engine a range, so the engine kept the rate. The engine exposes no command that controls the adaptation rate.

Two engine facts shape the design. `getLightingAt <object>` returns `[ambientLightColor, ambientLightBrightness, dynamicLightColor, dynamicLightBrightness]` and is the only command that folds local dynamic light into one value. `apertureParams` returns the engine's own `estimatedLuminance` and `blinding`. Neither brightness element has a documented unit.

The engine's own `setApertureNew` also reacts to the rendered scene: the less sky in view, the wider the aperture opens. Pinning the aperture gives AEE full control of the rate, and it removes that scene-driven response. AEE therefore measures the scene itself, including a sky-visibility raycast.

## Decision

1. AEE computes the adapted aperture every frame and pins it with `setApertureNew [_v, _v, _v, 1]`. With minimum equal to standard equal to maximum, the engine cannot adapt inside a range, so AEE owns the rate. The command needs HDR and must run after mission start.

2. The model runs in base-10 log-luminance. A fast pupil branch lags a slow cone and rod pair. The CIE 191:2010 mesopic photopic fraction blends the cone pool against the rod pool, and the fast branch blends over the slow result.

3. The scene luminance combines the core illuminance model (`aee_core_ambientLux`, `aee_core_dynamicLux`), the engine `getLightingAt` value, and the `apertureParams` blinding term. A five-ray sky cast scales the ambient term. A local light is not scaled by the sky, so a torch lights a closed room.

4. Exactly one writer owns the camera. The eye model stands down while `currentVisionMode != 0`, because night vision goggles and thermal sights set their own fixed exposure. The stand-down writes `setAperture -1` to hand the camera back. No aperture write remains in `atmos`.

5. The operator tunes the model from CBA settings under `AEE Optics` > `Eye Adaptation`. Debug hooks on `missionNamespace` force a scene luminance (`aee_optics_eyeForceLux`), freeze the state (`aee_optics_eyeFreeze`), and force a day or night target (`aee_optics_eyeForceMode`). A muzzle flash adds a separate transient term through `aee_optics_eyeFlashLux` and `aee_optics_eyeFlashUntil`.

## Local-light sensing limits

- `getLightingAt` folds local dynamic light, but it returns `[]` on a logic, it is off on a dedicated server, and it is gated by the local player's night-vision state. It is therefore client-only and enters the model only through a tunable scale.
- The engine exposes no light registry, no per-light colour, intensity or range readback, and no documented unit for either brightness element. `lightIsOn` works on street-lamp-class objects only.
- `apertureParams` `estimatedLuminance` and `blinding` are read for diagnostics. The blinding term is wired through an off-by-default scale.
- The core dynamic-light scan already covers lamps, fires, flares, vehicle lights and the weapon light. It stays in the `max` chain, so local light still drives the model if `getLightingAt` proves blind in game. Raising `eyeLocalLuxScale` is the first tuning step.

## UNSOURCED values

The per-constant register is in the plan. The values marked UNSOURCED, and repeated beside the value in code, are: the mesopic smoothstep shape, the pupil diameter clamps (1.9 and 8.0 mm), the cone dark-adaptation tau (derived), the light-adaptation tau, the fast-branch blend, the scene reflectance, and the three engine scales plus the muzzle-flash lux scale. No value is invented without that marking.

## Consequences

- **Good**: AEE owns the eye adaptation rate at human speeds, night and day, entering and leaving buildings, and for every light source. The model is pure and testable: the kernels run in `tools/tests/sqf_lite.py`.
- **Cost**: The pin removes the engine's own scene response, so AEE must measure the scene itself. The local-light term depends on an engine value with no documented unit.
- **Risk**: A wrong local scale under-lights or over-lights a scene. All three scales are operator-tunable, and the blinding term is off by default.

## References

- Issue #141: eye adaptation rate.
- `addons/optics/functions/eye/`: the model, the driver and the debug hooks.
- BI wiki: `setAperture`, `setApertureNew`, `getLightingAt`, `apertureParams`.
- CIE 191:2010 (mesopic photometry); CIE 018:2019 (luminous efficacy).
- de Groot and Gebhard 1952, JOSA 42(7):492 (pupil diameter fit).
- Meethal 2021, Sci Rep 11:21090 (pupil latency and redilation ratio).
- Rushton 1961, J Physiol 156:166 (rod dark adaptation).
- Lamb and Pugh 2004, Prog Retin Eye Res 23:307-380 (biphasic dark curve).
- Hecht, Haig and Chase 1937, J Gen Physiol 20:831 (cone-rod break).
