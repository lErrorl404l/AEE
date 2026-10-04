# ADR-009: NVG Imperfection Ownership

Status: Accepted
Date: 2026-10-04
Decision: The night-vision tube model owns the image-intensifier imperfections. Two generated RGBA textures on two `RscPicture` overlay controls carry the static spatial flaws. Every temporal flaw adjusts an EXISTING post-process handle. No new effect handle is created.

## Context

The night-vision view read as a clean green filter. A real image intensifier is not clean. It shows fixed-pattern noise, dark spots, bright emission points, fibre-optic honeycomb reticulation, a bright-source washout with a slow recovery, automatic-gain-control breathing, dark-scene scintillation, edge distortion and veiling glare. The operator asked for the BAD effects, not only the good.

An audit of `fnc_applyNVGTubeModel.sqf` showed the tube model already covers gain, shot noise, MTF, bloom, vignette, phosphor tint, temperature, warm-up and persistence. The missing flaws are the static spatial ones and the explicit temporary-blinding recovery. Nothing may be duplicated.

The ADR number is 009 because the in-flight `aee-night-sky-debug` plan reserves ADR-008.

## Decision

1. Two generated textures carry the static spatial flaws. `nvg_blemishes.png` carries the dark spots, the bright emission points and the fixed-pattern mottle. `nvg_reticulation.png` carries the honeycomb lattice. Each bakes a circular alpha mask, so nothing draws on the black surround. `tools/gen_nvg_imperfections.py` generates both with a fixed seed. `hemtt utils paa convert` writes the shipped PAAs.

2. Two `RscPicture` controls on a new `RscTitles` class (`idd 10780`, controls `idc 1010` and `idc 1011`) present the textures. The parent fades each control with `ctrlSetFade` at run time. Fade 0 is opaque and fade 1 is transparent. ACE3's `fnc_pfeh` proves `ctrlSetFade` on an `RscPicture` overlay.

3. The temporal flaws reuse the EXISTING handles only: ColorCorrections, DynamicBlur, RadialBlur and FilmGrain. No `ppEffectCreate` call is added, so the alt-tab recreate block in the parent is unchanged.

4. Six pure kernels do the maths: `fnc_nvgTierIndex`, `fnc_nvgBlemishField`, `fnc_nvgAgcBreathing`, `fnc_nvgBlindingEnvelope`, `fnc_nvgScintillation` and `fnc_nvgPincushion`. They run from their real SQF through `tools/tests/sqf_lite.py`.

5. Nine CBA settings under `AEE Night Vision` > `Imperfections` drive the model. Four force hooks and a debug toggle on `missionNamespace` support a visual acceptance pass.

## Engine limits

- **No radial pincushion parameter.** The engine has `WetDistortion`, a geometric wave warp, but it is a water ripple with no radial coefficient and it cancels under water. No radial pincushion parameter exists. The edge read is therefore a blur approximation through the existing RadialBlur handle, and the true pincushion warp percent per generation is UNSOURCED.
- **RadialBlur video-option dependency.** RadialBlur does nothing when RADIAL BLUR is disabled in Video Options. For those players the edge read is a silent no-op. The other flaws are unaffected.
- **Uniform FilmGrain only.** FilmGrain applies noise across the whole screen. Per-pixel Poisson weighting needs a custom pixel shader. Scintillation therefore scales the uniform grain with the dark-scene photon count, not per pixel.
- **Overlay geometry.** The overlay is clipped to the tube circle by the baked alpha mask. The one in-game check is whether the mask lands on the engine's NVG circle at the player's aspect ratio.

## UNSOURCED values

The per-constant register is in `.omo/plans/aee-nvg-imperfections.md` and `docs/wiki/research/nvg-imperfections-dossier.md`. The values marked UNSOURCED, and repeated beside the value in code, are: the pincushion distortion percent per generation, the reticulation modulation depth, the scintillation index versus flux, the AGC pole or time constant, the numeric auto-gate open, close and recovery constants, the blinding envelope constants (`whiteMax`, `blackMin`, `contrastLoss`), the AGC breathing oscillation frequency (3.0 rad/s), the scintillation coefficients (0.55, 0.25, 0.5, 0.1), the blemish per-tier base array (0.85, 0.55, 0.30, 0.15), the FPN mottle spatial realisation, and the veiling-glare band above the sourced 2.13 percent low end. The `ColorCorrections` non-zero desaturation weight is UNSOURCED: it is a repo comment, not a wiki statement. No value is invented without that marking.

## Consequences

- **Good**: the tube shows the flaws a real intensifier shows. The static flaws are cheap (one static draw per control). The temporal flaws cost one `ppEffectAdjust` per tick on handles that already exist. The model is testable: the kernels run in the test harness.
- **Cost**: one in-game check is needed for the overlay geometry. RadialBlur's video-option dependency leaves the edge read silent for some players.
- **Risk**: a miscalibrated master multiplier over- or under-plays every flaw. Every magnitude is operator-tunable, and the master gate turns the whole set off.

## References

- Issue #215: night-vision imperfections.
- `.omo/plans/aee-nvg-imperfections.md`: the plan and the 24-row source register.
- `docs/wiki/research/nvg-imperfections-dossier.md`: the source register.
- MIL-I-49428(CR) 06-NOV-1989: sections 3.6.6, 3.6.12, 3.6.15.2, 3.6.21, 3.11.19, Table III.
- Hamamatsu F1094-077 datasheet TMCPB0106E (MCP pitch).
- ACE3 `addons/nightvision/functions/fnc_pfeh.sqf` and `fnc_scaleCtrl.sqf` (`ctrlSetFade` overlay proof).
- BI wiki: `ppEffectCreate`, `ppEffectAdjust`, `ctrlSetFade`, `cutRsc`.
