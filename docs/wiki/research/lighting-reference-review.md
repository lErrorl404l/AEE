# Lighting Reference Review

AEE reviewed three lighting values against a reference the operator calls
realistic. The reference is Steam Workshop item 3587581054, "Highlights - HDR
& Lighting Suite [HLS]", by Tyrr. It is a pure config override. It publishes no
licence. AEE copies no value, array or file from it. The reference is a
comparison against the vanilla baseline only.

The baseline is the vanilla Altis world config, `a3/map_altis/config.cpp`. AEE
read the reference from an unpacked scratch tree.

## Why the reference reads realistic

The reference re-authors the `HDRNewPars` filmic tone curve and all 42 day
keyframes. It leaves bloom, the aperture range and `nightShift*` untouched. It
moves `tonemapExposureBias` from 1.0 to 1.3. It dims the stars from 25 to 20.
It adds no light source and no post-process grade.

AEE keeps the vanilla tone curve and applies a gated `ColorCorrections` grade.
`HDRNewPars` is global, so AEE treats it with more care than the reference.
AEE already matches vanilla on bloom, the aperture ratio and `nightShift*`.

## Item 1: Stars

Verdict: AEE over-brightened the stars. The change is warranted.

AEE set `starEmissivity` to 40. That is 1.6 times the vanilla 25. It has no
physical source. It is an aesthetic proxy between two other mods (Fluffys 30
and Real Lighting 60). The reference dims the stars to 20, below vanilla. The
operator calls the reference realistic, so the direction is down. The
defensible value is the vanilla baseline, 25.

AEE also publishes a run-time `starScale` of 0.80 to 1.30 by climate class.
That scale multiplies AEE's own star-light coefficient, not `starEmissivity`.
Its direction follows the lower atmospheric extinction in cold, dry and arid
air. It is bounded and disclosed as UNSOURCED. AEE keeps it.

| Value | Vanilla Altis | Reference | Before | After | Source | Operator-visual |
| --- | --- | --- | --- | --- | --- | --- |
| `starEmissivity` | 25 | 20 | 40 | 25 | vanilla baseline (`a3/map_altis/config.cpp`) | yes |
| `starScale` (run time) | none | none | 0.80 to 1.30 | 0.80 to 1.30 | UNSOURCED aesthetic proxy | yes |

## Item 2: Night floor

Verdict: AEE does not depart from vanilla. No change is warranted.

The review brief named the `DayLighting` override as AEE's largest departure
from the reference. The values show the opposite. AEE's `deepNight` and
`fullNight` match the vanilla keyframes to within 0.001. The `deepNight` first
triplet is 0.0049, 0.0098, 0.0098 against the vanilla 0.005, 0.01, 0.01. AEE is
2 per cent darker, not brighter. The `fullNight` triplets differ only by a
0.001 swap between two red channels. The rainy `fullNight` last triplet is
0.059 against 0.06. The override is structural: the engine reads `DayLighting`
through the world class chain, so AEE re-homes it with the vanilla values.

The operator reports "midnight too dark". This override cannot cause that
report, because it equals the vanilla floor. The reference also leaves
`DayLighting` at vanilla. The current value is justified. AEE keeps it.

| Keyframe | Vanilla Altis | Reference | Before | After | Source | Operator-visual |
| --- | --- | --- | --- | --- | --- | --- |
| `deepNight` (bright) | {0.005,0.01,0.01},... | vanilla | {0.0049,0.0098,0.0098},... | unchanged | vanilla baseline | no |
| `fullNight` (bright) | {0.182,0.213,0.25},... | vanilla | {0.182,0.213,0.25},... | unchanged | vanilla baseline | no |
| `deepNight` (rainy) | {0.005,0.01,0.01},... | vanilla | {0.0049,0.0098,0.0098},... | unchanged | vanilla baseline | no |
| `fullNight` (rainy) | {0.023,...},...,{0.08,0.06,0.06} | vanilla | {0.023,...},...,{0.08,0.059,0.059} | unchanged | vanilla baseline | no |

The remaining day keyframes keep the base game value in both AEE and the
reference. Neither authors a day keyframe.

## Item 3: SimulWeather

Verdict: AEE leaves `SimulWeather` alone. No change is warranted.

The reference lowers `directLightCoef` to 0.25 and raises `autoBrightness` to
1. It treats the cloud light response as a realism idea. AEE keeps the vanilla
`SimulWeather`. AEE adds no new post-process and no new light source. The
change has no physical source. It is not clearly warranted, so AEE leaves it.

| Key | Vanilla Altis | Reference | Before | After | Source | Operator-visual |
| --- | --- | --- | --- | --- | --- | --- |
| `autoBrightness` | 0 | 1 | 0 (not overridden) | 0 | vanilla baseline | yes |
| `autoBrightnessStrength` | 0.1 | 0.8 | 0.1 (not overridden) | 0.1 | vanilla baseline | yes |
| `directLightCoef` | 1.0 | 0.25 | 1.0 (not overridden) | 1.0 | vanilla baseline | yes |
| `indirectLightCoef` | 0.04 | 0.075 | 0.04 (not overridden) | 0.04 | vanilla baseline | yes |

## The override structure is kept

AEE changes only the `starEmissivity` value. Every `CfgWorlds` block keeps its
vanilla parent. The re-open form `class X: X` is unchanged. No class is
re-emptied. The engine merges the values through the world class chain.

## Honest ceiling

AEE proves the resolved config values headless. AEE cannot prove the rendered
frame headless. The star dimming, the night darkness and the cloud light need
an operator in-game look. The star change is the only value a player can see
without a measurement.
