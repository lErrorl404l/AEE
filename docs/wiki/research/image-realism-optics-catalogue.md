# Image realism: optics and the scriptable post-process set

## Purpose

This note records what the Arma 3 engine can and cannot do for a normal-vision
image grade, an acuity pass, and thermal sensor imperfections. It names the
source for each claim. The design decision is in ADR-010.

## The supported post-process set

`ppEffectCreate` accepts these effects. The list is from BIKI
`ppEffectCreate`, capture 2024-10-06, read through the Wayback Machine.

- RadialBlur
- ChromAberration
- WetDistortion
- ColorCorrections
- DynamicBlur
- FilmGrain
- ColorInversion
- SSAO
- Resolution

There is no `Sharpen` effect. A search of the raw page, the 2013 list and a
code search returns no `ppEffectCreate ["Sharpen", ...]` call.

## Scene sharpening

Scene sharpening is the built-in video option "Sharpen Filter" on the AA and PP
tab. A mod cannot set a video option. The option description warns that it can
add grain or outlines.

The scriptable candidate is FilmGrain at a high `sharpness` and a low
`intensity`. The wiki names the `sharpness` parameter but does not state what
it sharpens. That it sharpens the scene is UNSOURCED.

Sharpening is a display choice. Contrast sensitivity is a band-pass function
that peaks near 4 cycles per degree and cuts off near 60 cycles per degree
(Campbell and Robson 1968, J Physiol, DOI 10.1113/jphysiol.1968.sp008574).
Sharpening does not add human acuity. It compensates render and display
modulation-transfer loss.

## Colour grading

The grade uses ColorCorrections. The parameter table is BIKI Post Process
Effects, Wayback capture 20240220225631. Brightness 0 is black, 1 is
unchanged. The colorize alpha is the saturation. The engine can desaturate but
cannot oversaturate.

The colour weights are the Rec.709 luma weights, 0.2126, 0.7152 and 0.0722.
These are the same luma that ASC CDL uses.

An always-on ColorCorrections is proven in community code (Liberation-RX,
GPL-3.0) and ZEN (GPL-3.0). The exact AEE defaults are UNSOURCED.

A true unsharp mask is not possible. The formula is

    sharpened = original + (original - blurred) * amount

with a detail radius of 0.5 to 2 pixels and a local-contrast radius of 30 to
100 pixels (Wikipedia Unsharp masking, summarising Gonzalez and Woods and
Polesel et al. 2000). The engine has no blur copy and no additive compositing.
The formula is the target the FilmGrain compromise is measured against, not a
runtime formula.

## Thermal sensor imperfections

Fixed-pattern noise is dark-signal non-uniformity plus photo-response
non-uniformity. A flat-field or non-uniformity correction removes it, and it
drifts with temperature, integration time and gain (Wikipedia fixed-pattern
noise, EMVA Standard 1288).

The noise-equivalent temperature difference is 30 to 200 mK for an uncooled
bolometer and near 10 mK for a cooled detector (Wikipedia
Noise-equivalent temperature, citing NMAB 1995). The existing thermal display
chain already derives the fixed-pattern amplitude from the device value. The
imperfections reuse that term.

Automatic gain control compresses the dynamic range. It produces a breathing
and washout artefact (Wikipedia Automatic gain control). The hunting timescale
is UNSOURCED.

Thermal blooming and haloing have no authoritative source. That value is
UNSOURCED. The bloom is modelled as a DynamicBlur spike, the same primitive the
night-vision model uses for halo.

## Limits

- No `Sharpen` ppEffect exists.
- No scriptable scene sharpening exists. The video option is operator-only.
- No true unsharp mask.
- The engine can only desaturate.
- The FilmGrain pass couples grain and sharpness. A small amount of grain is
  unavoidable.
- The thermal hunt timescale, the NUC refresh cadence, the wake-up burst
  interval and the bloom amplitude are UNSOURCED.

## References

- BIKI `ppEffectCreate`, Wayback capture 2024-10-06.
- BIKI Post Process Effects, Wayback capture 20240220225631.
- BIKI Performance Optimisation, capture 2025-01-11.
- Campbell and Robson 1968, J Physiol, DOI 10.1113/jphysiol.1968.sp008574.
- Wikipedia Unsharp masking, fixed-pattern noise, Noise-equivalent temperature,
  Automatic gain control and Thermography.
- EMVA Standard 1288.
- ADR-010, .omo/plans/aee-image-realism.md.
