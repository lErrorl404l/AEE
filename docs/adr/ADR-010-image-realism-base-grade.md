# ADR-010: Normal-Vision Base Grade and Thermal Sensor Imperfections

Status: Accepted
Date: 2026-10-04
Decision: AEE applies a normal-vision display grade and a FilmGrain acuity pass through two registry-owned effects, and adds four thermal sensor artefacts to the existing thermal display chain.

## Context

The operator asked for a less flat base image, more apparent detail, and the flaws a real thermal camera shows. The base game looks washed out at the default video settings.

The engine limits what a mod can do. The creatable post-process set is RadialBlur, ChromAberration, WetDistortion, ColorCorrections, DynamicBlur, FilmGrain, ColorInversion, SSAO and Resolution. There is no Sharpen effect. Scene sharpening is the built-in video option "Sharpen Filter", and a mod cannot set a video option. The engine can desaturate an image but cannot oversaturate it.

## Decision

1. The base grade owns its own ColorCorrections effect through the core registry, under the optics scope and the key "BaseGrade" at priority 1505. It never reuses the single-slot severe-weather ColorCorrections in fnc_managePostProcess, so the two never fight.

2. The acuity pass owns its own FilmGrain effect under the key "BaseAcuity" at priority 2505. FilmGrain sharpness at high value and low intensity is the only scriptable sharpening candidate. The engine has no Sharpen effect, so a true unsharp mask is not possible.

3. The grade applies on normal vision only. It gates on currentVisionMode 0 and stands down in NVG (1) and thermal (2). It also stands down on death, respawn, a camera change and the module disable. The stand-down neutralises the ColorCorrections before it disables the handles.

4. A missing handle is destroyed and recreated with the night-vision pattern. The effects survive alt-tab, a resize and an advanced optic.

5. The grade and the acuity pass are display aesthetic. Sharpening does not add human acuity. Contrast sensitivity is a band-pass function that peaks near 4 cycles per degree and cuts off near 60 cycles per degree (Campbell and Robson 1968). The acuity pass compensates render and display modulation-transfer loss only.

6. The thermal imperfections live in addons/thermal because they extend the existing thermal display chain. The four artefacts are a non-uniformity and blemish drift on the fixed-pattern noise, a temporal noise scale, an automatic-gain-control hunt, and a hot-source bloom. The existing FPN and NETD term is reused, not duplicated.

7. Every new effect has a missionNamespace force hook and a log line. The operator can force each artefact in the debug console.

## Limits

- No Sharpen ppEffect exists. No scriptable sharpening exists. The video option is operator-only.
- No true unsharp mask. The engine has no blur-copy and no additive compositing.
- The engine can only desaturate. The saturation weight stays in the range 0 to 0.5.
- FilmGrain couples grain and sharpness. A small amount of grain is unavoidable with the acuity pass.
- The FilmGrain sharpness parameter is named in the wiki but its effect on the scene is not documented. That it sharpens the scene is UNSOURCED.
- The thermal view, the felt grade and the felt sharpening need an operator game run to judge.

## UNSOURCED values

The per-constant register is in .omo/plans/aee-image-realism.md. The values marked UNSOURCED, and repeated beside the value in code, are: the exact grade contrast default, the exact black-point default, the FilmGrain sharpness effect on the scene, the AGC hunt timescale, the NUC refresh cadence, the wake-up burst interval, and the hot-source bloom amplitude. No value is invented without that marking.

## Consequences

- Good: the base grade deepens tone separation and the black point on normal vision, and the acuity pass raises apparent detail. The thermal view gains the flaws a real sensor shows. The effects are subtle by default and operator-tunable.
- Cost: the acuity pass adds a small amount of grain because the engine couples grain and sharpness. The thermal hunt and bloom add per-tick terms to the display chain.
- Risk: a grade that is too strong looks unnatural. Every value is operator-tunable, and the acuity pass can be disabled on its own.

## References

- Operator request: optic imperfections in general, realistic colour grading, and a little more sharpness on the base game.
- BIKI ppEffectCreate, capture 2024-10-06: the supported effect set.
- BIKI Post Process Effects, Wayback capture 20240220225631: the ColorCorrections and FilmGrain parameter tables.
- ASC CDL luma weights for Rec.709: 0.2126, 0.7152, 0.0722.
- ACES tone-mapping (docs.acescentral.com): an S-shaped tone curve.
- Campbell and Robson 1968, J Physiol, DOI 10.1113/jphysiol.1968.sp008574: contrast sensitivity.
- Wikipedia fixed-pattern noise and EMVA Standard 1288: FPN and NUC.
- Wikipedia Noise-equivalent temperature (citing NMAB 1995): NETD ranges.
- Wikipedia Automatic gain control: AGC breathing and washout.
- .omo/plans/aee-nvg-imperfections.md: the night-vision plan. Not duplicated here.
