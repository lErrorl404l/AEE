# ADR-014: Human-Vision Model for Normal Vision

Status: Accepted
Date: 2026-10-04
Decision: AEE derives the normal-vision display tone, contrast, white balance and mesopic tint from a published human-vision model. The model subsumes the aesthetic base grade in place and reuses its registry keys.

## Context

The normal-vision grade was a hand-tuned aesthetic look. The operator asked for an image that follows published human-vision science. The eye adaptation model already exists in `addons/optics/functions/eye/`. It publishes the adapted light level and the mesopic photopic fraction. It owns the aperture. The new work must read that state and add the colour and tone stages.

The engine limits the work. Arma 3 renders a low dynamic range image through a fixed display white. It has no HDR, no per-region adaptation, no chromatic-adaptation matrix and no scriptable sharpening. The creatable post-process set is RadialBlur, ChromAberration, WetDistortion, ColorCorrections, DynamicBlur, FilmGrain, ColorInversion, SSAO and Resolution. The model can express only part of each stage. The rest is a stated ceiling.

## Decision

1. The model has five stages. Stage 1 is light level and photoreceptor adaptation. Stage 2 is the tone response. Stage 3 is contrast sensitivity. Stage 4 is chromatic adaptation and white balance. Stage 5 is mesopic colour and the Purkinje shift.

2. The new pure kernels live in `addons/optics/functions/perception/`. They compute stages 2, 4 and 5. Stage 1 is read from the eye model and never written. Stage 3 is a stated ceiling, because the engine cannot filter. The kernels are pure. They use no missionNamespace, no GVAR or EGVAR, and no engine command. `tools/tests/sqf_lite.py` runs them in the test suite.

3. The model ships in three slices. Slice 1 ships the light and tone stage. Slice 2 ships the colour and tint stage. Slice 3 enables the model by default. The default switch is on. The photopic default keeps the colorize alpha at 0, so the default image is not desaturated. At the real CBA defaults the tone stage is active, so a full-identity assertion runs on the all-stages-neutral fixture, not on the CBA defaults.

4. The perception path subsumes the aesthetic base grade in place. The driver `addons/optics/functions/grade/fnc_applyBaseGrade.sqf` gains one branch. When the model is on, the driver calls `FUNC(perceptionParams)`. Otherwise it calls `FUNC(baseGradeParams)`. The operator reverses the branch through the `visionModelEnabled` setting. The legacy kernel output is unchanged.

5. The model reuses the registry keys `BaseGrade` (ColorCorrections at priority 1505) and `BaseAcuity` (FilmGrain at priority 2505). It creates no new key and no new effect. The proven registry ownership, the priority and the teardown tests survive.

6. The model reads the eye adaptation model's published state. It reads `aee_optics_eyeAdaptedLux` and `aee_optics_eyeMesopic`. It never writes the aperture. The eye model keeps the aperture, its rate, its `currentVisionMode != 0` gate and its `setAperture -1` stand-down. The driver does not chain onto the eye module.

7. The white target is the display white D65. The scene illuminant is the engine ambient colour from `getLightingAt`. The adaptation is a partial von Kries blend. The engine has no cone matrix, so the ColorCorrections blend slot carries a small complementary tint in the display domain.

8. A gap-closing test pins the contract and the identity image. `TestColorCorrectionsContract` pins the seven-element shape and each slot role. `TestNeutralFixtureIdentity` asserts the all-stages-neutral fixture. `TestDefaultPathColorizeAlpha` asserts the photopic default colorize alpha is 0. `TestIdentityDetectsDesaturation` proves the suite detects the black-and-white class. That class drained normal vision to grey, and no machine gate caught it before.

9. The model runs inside the existing 1.0 s client PFH. It adds at most one engine read per tick (`getLightingAt`). The pure kernels are arithmetic over a few numbers. It does not touch the 5 ms `aee_core_fnc_updateEnvironment` gate.

## The five stages and their sources

Stage 1, light level and photoreceptor adaptation. The eye adapts to the scene luminance. The model works in base-10 log luminance. Two slow pools, cones and rods, chase the target with first-order lags. This stage already exists in the eye module.

- Mesopic band 0.005 to 5.0 cd/m2. SOURCED to CIE 191:2010, restated in IES TM-12-12.
- The photopic fraction m is 0 pure scotopic to 1 pure photopic. SOURCED to CIE 191:2010.
- The smoothstep shape between the endpoints is UNSOURCED. CIE defines the band, not this curve.
- Photopic peak 555 nm at 683 lm/W. SOURCED to CIE 1924 and CIE 018:2019.
- Scotopic peak 507 nm at about 1700 lm/W. SOURCED to CIE 1951 and CIE 018:2019.

Stage 2, tone response. The retina compresses a wide luminance range into a narrow response. The standard form is the Naka-Rushton equation. SOURCED to Naka and Rushton 1966, DOI 10.1113/jphysiol.1966.sp008003. Above the photoreceptors the percept follows the CIE 1976 lightness function L*. SOURCED to CIE 15:2004 and ISO 11664-4. The exponent above the threshold is 1/3. The threshold is delta = 6/29. Weber and Fechner give a logarithmic response. Stevens gives a power law. SOURCED to Stevens 1957, restated in a secondary table.

Stage 3, contrast sensitivity. Contrast sensitivity is a band-pass function of spatial frequency. It peaks near 4 cycles per degree and cuts off near 60 cycles per degree. SOURCED to Campbell and Robson 1968, DOI 10.1113/jphysiol.1968.sp008574. The peak and cutoff numbers are a secondary reading of the paper figure. Barten 1999, SPIE PM72, gives the consolidated model. The engine cannot filter. This stage is a stated ceiling, not a deliverable.

Stage 4, chromatic adaptation and white balance. The eye adapts to the illuminant with the von Kries coefficient law. SOURCED to von Kries 1902. The modern form is CAT16. SOURCED to Li et al. 2017, DOI 10.1002/col.22131. The earlier CAT02 matrix is SOURCED to CIE 159:2004. The Bradford matrix is SOURCED to Lam 1985. The degree of adaptation D is partial. CIECAM02 defines D, and F is 0.8 for a dim surround, 0.9 for average and 1.0 for dark. SOURCED to CIE 159:2004.

Stage 5, mesopic colour and the Purkinje shift. Below about 5 cd/m2 the rods take over. Rods peak near 507 nm and cones near 555 nm. The world loses colour and shifts blue-green. The CIE 191:2010 photopic fraction m already gates this. The plan uses m to desaturate and to tint toward the scotopic hue. The exact desaturation and tint amplitudes are UNSOURCED.

## Per-constant source register

Every new constant is listed with its source, or marked UNSOURCED. The executor copies this marking beside the value in code and in the stringtable description.

| Constant | Value | Range | Source |
| --- | --- | --- | --- |
| Mesopic lower band | 0.005 cd/m2 | fixed | SOURCED: CIE 191:2010, restated in IES TM-12-12. |
| Mesopic upper band | 5.0 cd/m2 | fixed | SOURCED: CIE 191:2010. |
| Mesopic smoothstep shape | smoothstep | fixed | UNSOURCED: CIE defines the band, not this curve. Already in the eye mesopic weight kernel. |
| Photopic peak | 555 nm, 683 lm/W | fixed | SOURCED: CIE 1924 and CIE 018:2019. |
| Scotopic peak | 507 nm, about 1700 lm/W | fixed | SOURCED: CIE 1951 and CIE 018:2019. |
| CIE L* exponent | 1/3 | fixed | SOURCED: CIE 15:2004 and ISO 11664-4. |
| CIE L* threshold delta | 6/29, delta cubed 0.008856 | fixed | SOURCED: CIE 15:2004. |
| Naka-Rushton exponent n | 0.7 | 0.5 to 1.0 | Form SOURCED: Naka and Rushton 1966, DOI 10.1113/jphysiol.1966.sp008003. The exact n is UNSOURCED. |
| Naka-Rushton sigma | half-saturation luminance | adaptive | Form SOURCED. The exact sigma is UNSOURCED and tunable. |
| Stevens brightness exponent | 0.33 | fixed | SOURCED: Stevens 1957, secondary table. |
| Weber fraction | 0.01 to 0.02 | fixed | SOURCED: Weber and Fechner, textbook. The exact value is UNSOURCED. |
| CSF peak | about 4 cycles/degree | fixed | SOURCED: Campbell and Robson 1968, secondary reading. |
| CSF cutoff | about 60 cycles/degree | fixed | SOURCED: Campbell and Robson 1968, secondary reading. |
| Reinhard operator | Ld = L / (1 + L) | fixed | SOURCED: Reinhard et al. 2002, DOI 10.1145/566654.566575. |
| Reinhard key | 0.18 | 0.09 to 0.36 | SOURCED: Reinhard et al. 2002. |
| Hable constants A to F | 0.15, 0.50, 0.10, 0.20, 0.02, 0.30 | fixed | SOURCED: Hable 2010, practitioner conference source. |
| ACES Filmic approximation | Narkowicz fit | fixed | SOURCED: Narkowicz 2016, practitioner source. Not the Academy curve. |
| CAT16 matrix | M_CAT16 | fixed | SOURCED: Li et al. 2017, DOI 10.1002/col.22131. |
| CAT02 matrix | M_CAT02 | fixed | SOURCED: CIE 159:2004. |
| Bradford matrix | M_BFD | fixed | SOURCED: Lam 1985, textbook restatement. |
| Adaptation degree D | F times the CIECAM02 expression | 0 to 1 | SOURCED: CIE 159:2004. |
| Surround factor F | 0.9 | 0.8 to 1.0 | SOURCED: CIE 159:2004. |
| D65 white | x 0.3127, y 0.3290 | fixed | SOURCED: CIE 15:2004 and ITU-R BT.709-6. |
| D50 white | x 0.3457, y 0.3585 | fixed | SOURCED: CIE 15:2004. |
| Rec.709 luma weights | 0.2126, 0.7152, 0.0722 | fixed | SOURCED: ITU-R BT.709-6. |
| ColorCorrections slot order | brightness, contrast, offset, blend, colorize, weights, radial | fixed | SOURCED: BIKI Post Process Effects, Wayback capture 2024-02-20. |
| ColorCorrections identity | colorize alpha 0 | fixed | SOURCED: BIKI, alpha 0 is original colour, alpha 1 is B&W times the colour. |
| Radial default | -1, -1, 0, 0, 0, 0, 0 | fixed | SOURCED: BIKI, Arma 3 radial default. |
| FilmGrain defaults | 0.005, 1.25, 2.01, 0.75, 1.0, 0 | fixed | SOURCED: BIKI, Arma 3 defaults. |
| Reference illuminance anchors | 0.0001 lx to 100000 lx | fixed | SOURCED: IES Handbook and CIE 011, secondary restatement. |
| Mid-grey reflectance | 0.18 | fixed | UNSOURCED as a CIE constant. It is a photographic convention. |
| Lambertian relation | L = rho E / pi | fixed | SOURCED: standard radiometry. |
| Purkinje tint vector | blue-green toward 507 nm | fixed | SOURCED: CIE 1951 scotopic peak. The tint amplitude is UNSOURCED. |
| Purkinje desaturation amplitude | 0.3 | 0 to 0.5 | UNSOURCED. Operator-tunable. |
| Tone calibration gain k | 1.0 | calibrated | UNSOURCED. The affine cannot express a curve. The tangent is a stand-in. |
| Tone contrast clamp | 0.8 to 1.6 | fixed | UNSOURCED. Matches the legacy base-grade clamp. |
| Tone offset clamp | -0.05 to 0.05 | fixed | UNSOURCED. BIKI says the offset range is 0 and up. Negative is proven in community code. |
| White-balance blend cap | 0.25 | 0 to 0.25 | UNSOURCED. A blend toward a solid colour washes out the image. |
| Display-RGB diagonal gain | clamp(2 - illuminant, 0, 1) | fixed | UNSOURCED. The engine has no cone matrix, so the display diagonal is a stand-in. |
| Luma floor in the illuminant kernel | small positive | fixed | UNSOURCED. A guard against a divide by zero. |

## The honest engine ceiling

The engine renders a low dynamic range image through a fixed display white. The eye sees about six decades of luminance and adapts per region. The gap is the following list. The model states each limit in code and in the docs.

1. No HDR. The engine display range is small. The model cannot show the true luminance ratio. It maps the eye response onto a compressed display.
2. No per-region adaptation. ColorCorrections is a global effect. The eye adapts locally. The model cannot reproduce local adaptation, glare recovery per patch, or Troxler fading.
3. No chromatic-adaptation matrix. ColorCorrections has no matrix. It has a blend slot and a colorize slot. The model approximates the CAT16 diagonal gain with a small blend toward the adapted white. A full 3 by 3 matrix is impossible.
4. No physical glare or bloom. The engine bloom is a fixed video option. The model cannot add a physical point-spread glare.
5. No sharpening and no CSF filter. The model cannot add a band-pass. FilmGrain is a display aesthetic. It does not add human acuity.
6. No oversaturation. ColorCorrections desaturates only. The saturation weight stays in the range 0 to 0.5.
7. No absolute luminance. The display white is fixed. The model cannot show 10 to the 5 cd/m2.
8. No afterimages, no Stiles-Crawford effect, no metamerism and no Purkinje motion. These have no engine primitive.

The map from model stage to primitive:

| Model stage | Primitive | Fidelity |
| --- | --- | --- |
| Exposure and light adaptation | `setApertureNew` aperture pin, owned by the eye model | Physical rate, engine display limit |
| Tone and contrast | ColorCorrections brightness, contrast, offset | Affine tangent only, not a curve |
| White balance | ColorCorrections blend slot toward the adapted white | Small tint, not a matrix |
| Mesopic colour and Purkinje | ColorCorrections colorize slot and desaturation alpha | Desaturate and re-tint, not an LMS shift |
| Acuity | FilmGrain at high sharpness and low intensity | Aesthetic only |
| CSF band-pass | none | Not possible |
| HDR and local adaptation | none | Not possible |

## Assurance

No UK MOD or NATO defence standard governs these vision constants. Civilian CIE, ISO and ITU values apply. Def Stan 00-250 governs human factors generally. If a MOD standard applied, it would take precedence over the civilian source. No value is invented without the source marking above.

## UNSOURCED values

The values marked UNSOURCED, and repeated beside the value in code and in the stringtable description, are the mesopic smoothstep shape, the Naka-Rushton exponent and sigma, the exact Weber fraction, the Purkinje tint and desaturation amplitudes, the tone calibration gain, the tone contrast and offset clamps, the white-balance blend cap, the display-RGB diagonal gain and the illuminant luma floor. Mid-grey reflectance is a photographic convention, not a CIE constant.

## Consequences

- Good: the image follows a published model of eye adaptation, tone, white balance and mesopic colour. Every constant is traced or marked. The model subsumes the base grade in place, so the proven registry ownership and the teardown tests survive.
- Cost: the model adds one engine read per tick and a few arithmetic kernels. The engine can only approximate the white balance and cannot add the CSF band-pass.
- Risk: a wrong constant looks unnatural. Every value is operator-tunable, and the model can be disabled on its own. The in-game look needs an operator game run.
- Gap closed: the identity-at-default test pins the ColorCorrections contract and detects the black-and-white class that shipped before.

## References

- BIKI Post Process Effects, Wayback capture 20240220225631: the ColorCorrections and FilmGrain parameter tables.
- BIKI `getLightingAt`, capture 20250120023422: the ambient light colour element.
- CIE 15:2004 and ISO 11664-4: the CIE 1976 L* function.
- CIE 159:2004: CIECAM02, the CAT02 matrix and the degree of adaptation D.
- CIE 018:2019, CIE 191:2010 and IES TM-12-12: photopic and scotopic response, and the mesopic band.
- CIE 1951 and CIE 1924: the scotopic V prime and the photopic V functions.
- ITU-R BT.709-6: the display white D65 and the Rec.709 luma weights.
- Naka and Rushton 1966, DOI 10.1113/jphysiol.1966.sp008003: the retinal response form.
- Campbell and Robson 1968, DOI 10.1113/jphysiol.1968.sp008574: contrast sensitivity.
- von Kries 1902, Li et al. 2017, DOI 10.1002/col.22131, and Lam 1985: chromatic adaptation.
- Reinhard et al. 2002, DOI 10.1145/566654.566575: the tone operator.
- `docs/adr/ADR-010-image-realism-base-grade.md`: the subsumed base grade and the acuity pass.
- `docs/adr/ADR-007-eye-adaptation-ownership.md`: the aperture and the eye adaptation rate.
- `.omo/plans/aee-vision-model.md`: the per-constant register and the slice plan.
