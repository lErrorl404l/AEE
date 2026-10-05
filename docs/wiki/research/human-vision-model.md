# The human-vision model for normal vision

## Purpose

This note records the human-vision model behind the normal-vision grade. It
names the five stages, the source for every constant, and the honest limit of
what the Arma 3 engine can express. The design decision is in ADR-014. The
per-constant register is repeated below with the same source marking used
beside each value in the code.

## The five stages

The model has five stages. The engine can express only part of each stage.

### Stage 1. Light level and photoreceptor adaptation

The eye adapts to the scene luminance. The model works in base-10 log
luminance. Two slow pools, cones and rods, chase the target with first-order
lags. The pupil sets retinal illuminance with a fast branch. This stage
already exists in the eye adaptation model. The perception path reads its
published state and never writes the aperture.

- The mesopic band is 0.005 to 5.0 cd/m2. SOURCED: CIE 191:2010, restated in IES TM-12-12.
- The photopic fraction m is 0 for pure scotopic to 1 for pure photopic. SOURCED: CIE 191:2010.
- The smoothstep shape between the endpoints is UNSOURCED. CIE defines the band, not this curve.
- The photopic peak is 555 nm at 683 lm/W. SOURCED: CIE 1924 and CIE 018:2019.
- The scotopic peak is 507 nm at about 1700 lm/W. SOURCED: CIE 1951 and CIE 018:2019.
- The pupil steady diameter is from de Groot and Gebhard 1952. Already used.

### Stage 2. Tone response

The retina compresses a wide luminance range into a narrow response. The
standard form is the Naka-Rushton equation, R equals Rmax times I to the n,
divided by the sum of I to the n and sigma to the n. SOURCED: Naka and
Rushton 1966, DOI 10.1113/jphysiol.1966.sp008003.

Above the photoreceptors the percept follows the CIE 1976 lightness function
L*. SOURCED: CIE 15:2004 and ISO 11664-4. The exponent above the threshold is
1/3. The threshold is delta = 6/29, so delta cubed is about 0.008856.

Weber and Fechner give a logarithmic response. Stevens gives a power law with
a brightness exponent near 0.33. SOURCED: Stevens 1957, restated in a
secondary table. The model uses the Naka-Rushton form with the CIE L* percept
as the tone model. The engine applies an affine, so the kernel uses the
first-order tangent at the adapted operating point, not the curve.

### Stage 3. Contrast sensitivity

Contrast sensitivity is a band-pass function of spatial frequency. It peaks
near 4 cycles per degree and cuts off near 60 cycles per degree. SOURCED:
Campbell and Robson 1968, DOI 10.1113/jphysiol.1968.sp008574. The peak and
cutoff numbers are a secondary reading of the paper figure. Barten 1999, SPIE
PM72, gives the consolidated model. The engine cannot filter. This stage is a
stated ceiling, not a deliverable.

### Stage 4. Chromatic adaptation and white balance

The eye adapts to the illuminant with the von Kries coefficient law, a
diagonal gain in cone space. SOURCED: von Kries 1902. The modern form is
CAT16. SOURCED: Li et al. 2017, DOI 10.1002/col.22131. The earlier CAT02
matrix is SOURCED: CIE 159:2004. The Bradford matrix is SOURCED: Lam 1985.

The degree of adaptation D is partial. CIECAM02 defines D = F times (1 minus
(1/3.6) times exp((minus LA minus 42) divided by 92)). F is 0.8 for a dim
surround, 0.9 for average and 1.0 for dark. SOURCED: CIE 159:2004. The model
uses D with F = 0.9 as the default.

The display white is D65 at x = 0.3127, y = 0.3290. SOURCED: CIE 15:2004 and
ITU-R BT.709-6. D50 is x = 0.3457, y = 0.3585. The engine renders to Rec.709
and sRGB, so D65 is the target white. The scene illuminant is estimated from
the engine ambient colour.

### Stage 5. Mesopic colour and the Purkinje shift

Below about 5 cd/m2 the rods take over. Rods peak near 507 nm and cones near
555 nm. The world loses colour and shifts blue-green. The CIE 191:2010
photopic fraction m gates this. The model uses m to desaturate and to tint
toward the scotopic hue. The exact desaturation and tint amplitudes are
UNSOURCED.

## The base anchor and the small bound

The normal-vision grade is anchored to the base game's own default grade. AEE
reads the class `CfgPostProcessTemplates >> Default >> colorCorrections` from
`a3\functions_f\config.cpp` line 3553 of `functions_f.pbo` (build 2025-08-11) at
run time. The read runs once per session and the result is cached. The value is
neutral: brightness 1, contrast 1, offset 0. AEE keeps the scalar triple
`[1, 1, 0]`. AEE never ships or copies the full vanilla array. The weight array
and the colorize array are AEE's own.

The grade is the anchor plus a small bounded deviation, computed in
`fnc_perceptionBaseGrade`. The bounds are contrast +0.00 to +0.08, offset -0.02
to 0.00, brightness -0.03 to +0.03 and a desaturation alpha 0 to 0.10. The
default tone strength is 0.25. On the neutral vanilla anchor the default grade
is about contrast 1.04, brightness 1.0, offset -0.008 and colorize
`[1, 1, 1, 0]`.

The default path ships no tint. `visionPurkinjeStrength` defaults to 0,
`visionMesopicDesaturation` defaults to 0 and `visionWhiteBalance` defaults to
false. At those defaults the mesopic kernel returns `[1, 1, 1, 0]` for every
mesopic fraction, and the blend stays `[0, 0, 0, 0]`. The mesopic, illuminant
and chromatic-adaptation kernels stay as the opt-in experimental path. The
mesopic band is 0.005 to 5.0 cd/m2 (CIE 191:2010). The Purkinje hue direction
is blue-green toward 507 nm (CIE 1951).

## Per-constant source register

Every new constant is listed with its source, or marked UNSOURCED. The code
carries the same marking beside the value, and the stringtable description
carries it too.

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
| Illuminant luma floor | small positive | fixed | UNSOURCED. A guard against a divide by zero. |
| Vanilla default anchor | `[1, 1, 0]` | fixed | SOURCED: `functions_f.pbo`, `a3\functions_f\config.cpp` line 3553, class `CfgPostProcessTemplates >> Default >> colorCorrections`, build 2025-08-11. Neutral scalar triple only. The full vanilla array is not shipped or copied. |
| Anchor fallback | `[1, 1, 0]` | fixed | SOURCED: the same as the vanilla default anchor. Used when the raw array is absent, malformed or out of range. |
| Contrast delta bound | `+0.00` to `+0.08` above the anchor | fixed | UNSOURCED: a small contrast lift. Operator-tunable by the clamp. |
| Offset delta bound | `-0.02` to `0.00` from the anchor | fixed | UNSOURCED: a small black-point deepen. |
| Brightness delta bound | `-0.03` to `+0.03` from the anchor | fixed | UNSOURCED: a small exposure nudge. |
| Desaturation alpha bound | `0` to `0.10` | fixed | SOURCED direction: the engine desaturates only (BIKI). The amplitude is UNSOURCED. |
| Default tone strength | `0.25` | 0 to 1 | UNSOURCED: scales the tone kernel into the bound. |
| Default white balance | `false` | bool | UNSOURCED: the engine ambient is green-biased, so full adaptation ships a cast. |
| Default mesopic desaturation | `0` | 0 to 0.5 | UNSOURCED: the operator rejects the tint. |
| Default Purkinje strength | `0` | 0 to 1 | UNSOURCED: the operator rejects the tint. The hue direction is SOURCED: CIE 1951. |

## The honest engine ceiling

The engine renders a low dynamic range image through a fixed display white.
The eye sees about six decades of luminance and adapts per region. The gap is
the following list. The model states each limit in the code and in this note.

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

## Performance budget

The model runs inside the existing 1.0 s client per-frame handler. It adds at
most one engine read per tick, the `getLightingAt` ambient read for the white
balance. The pure kernels are arithmetic over a few numbers. The model does
not touch the 5 ms `aee_core_fnc_updateEnvironment` gate, which is a server
tick on a different path. The work is client-local and negligible at one tick
per second. A machine profile on a live server is operator-only.

Signed off: the model is accepted at this cost. It extends no gate and adds
no periodic work beyond the one second tick that already runs. The client
tick and the server tick stay separate.

## Assurance

No UK MOD or NATO defence standard governs these vision constants. Civilian
CIE, ISO and ITU values apply. Def Stan 00-250 governs human factors
generally. If a MOD standard applied, it would take precedence over the
civilian source. No value is invented without the source marking above. The
values marked UNSOURCED are the mesopic smoothstep shape, the Naka-Rushton
exponent and sigma, the exact Weber fraction, the Purkinje tint and
desaturation amplitudes, the tone calibration gain, the tone contrast and
offset clamps, the white-balance blend cap, the display-RGB diagonal gain and
the illuminant luma floor.

## Follow-up: base-game lighting gaps (not implemented)

A survey of six Workshop lighting mods found gaps in the AEE environment
configuration. The items below are ideas re-implemented from mods with no
licence. They are not copied code. None is implemented. They are candidates for
a follow-up plan. No file under `addons/environmental` is changed here.

(a) Complete `HDRNewPars` globally. The AEE override in
`addons/environmental/config.cpp` sets only `nvg*` and `DOFPars`. The complete
world tone map is the largest single gap. It covers bloom, the tone map,
`eyeAdaptFactorLight`, `eyeAdaptFactorDark`, `nightShift*`, `starEmissivity`
and `dynLightMinBrightness*`.

(b) `starEmissivity`. The surveyed mods use 30 to 60. A first try is 40.

(c) The Star Light brightness coefficient. The star catalogue and the
limiting-magnitude model need the moon phase, `getLighting` element 1, the
count of nearby houses, and the overcast and fog fades.

(d) `DayLighting >> deepNight` and `DayLighting >> fullNight` keyframes. These
are the only lever on night darkness.

(e) Rain-scaled film grain. Low priority.

## References

- BIKI Post Process Effects, Wayback capture 20240220225631: the ColorCorrections and FilmGrain parameter tables.
- BIKI getLightingAt, capture 20250120023422: the ambient light colour element.
- CIE 15:2004 and ISO 11664-4: the CIE 1976 L* function.
- CIE 159:2004: CIECAM02, the CAT02 matrix and the degree of adaptation D.
- CIE 018:2019, CIE 191:2010 and IES TM-12-12: photopic and scotopic response, and the mesopic band.
- CIE 1951 and CIE 1924: the scotopic V prime and the photopic V functions.
- ITU-R BT.709-6: the display white D65 and the Rec.709 luma weights.
- Naka and Rushton 1966, DOI 10.1113/jphysiol.1966.sp008003: the retinal response form.
- Campbell and Robson 1968, DOI 10.1113/jphysiol.1968.sp008574: contrast sensitivity.
- von Kries 1902, Li et al. 2017, DOI 10.1002/col.22131, and Lam 1985: chromatic adaptation.
- Reinhard et al. 2002, DOI 10.1145/566654.566575: the tone operator.
- Barten 1999, SPIE PM72: the consolidated contrast-sensitivity model.
- ADR-014: the design decision. ADR-010: the subsumed base grade. ADR-007: the eye adaptation ownership.
