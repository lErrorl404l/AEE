# NVG Imperfection Source Register

This dossier records the per-constant source register for the night-vision
imperfection model (issue #215). It is written by the plan and mirrors
`.omo/plans/aee-nvg-imperfections.md`. Every value carries a source or is
marked UNSOURCED.

Sourcing key: **[P]** primary document read. **[P-W]** primary via Wayback.
**[C]** community wiki or forum. **[PROJECT]** already in this repository
with its own citation. **[UNSOURCED]** no primary obtained.

The generated textures carry the static flaws. `tools/gen_nvg_imperfections.py`
writes both PNGs with a fixed seed and records the regeneration commands in
its module docstring.

| Constant | Value | Source | State |
| --- | --- | --- | --- |
| Halo diameter, MX-10160/AVS-6 | <=1.47 mm | MIL-I-49428(CR), 06-NOV-1989, section 3.6.9 | [P] |
| Halo diameter, MX-10160B | 0.4-1.25 mm | Litton MX-10160B datasheet | [P] |
| Halo, Gen III / Gen II+ | 0.5533 / 0.2388 mm | Cui et al. 2012, Chinese Optics Letters 10(6) 060401 | [PROJECT] |
| Dark spot counts and sizes | zone 1/2/3 table | MIL-I-49428 Table III, section 3.6.21 | [P] |
| Dark spot contrast threshold | 30 percent | MIL-I-49428 section 3.6.21 | [P] |
| Type-B ion-barrier hole | <=125 um, <=10 per tube | MIL-I-49428 section 3.11.19; MX-10160-GS section 3.4.4.3.1 | [P] |
| Fixed-pattern noise, multi-to-multi | <= +/-10 percent | MIL-I-49428 section 3.6.12 | [P] |
| Chicken-wire fibre diameter | <=0.0009 in (~22.9 um) | MIL-I-49428 section 3.11.4 | [P] |
| Chicken-wire incidence by length | Table I | MIL-I-49428 Table I | [P] |
| MCP channel and pitch | 6 um channel, 7.5 um pitch | Hamamatsu F1094-077 datasheet TMCPB0106E | [P] |
| AGC fluctuation, drift, overshoot | +/-10 percent, +/-15 percent over 2 min, <=40 percent | MIL-I-49428 sections 3.6.6, 3.11.6, 3.11.18 | [P] |
| AGC rise time | <=7 s to 50 percent | MIL-I-49428 section 3.11.6 | [P] |
| Output persistence | <=0.15 percent within 300 ms | MIL-I-49428 section 3.6.22. This is PHOSPHOR persistence, NOT gate recovery | [P] |
| Veiling glare calibration standard | <=2.13 percent | MIL-I-49428 section 3.6.15.2 | [P] |
| Centre and peripheral resolution | >=36 lp/mm | MIL-I-49428 section 3.6.16 | [P] |
| MTF at 2.5/7.5/15/25 lp/mm | 83/58/28/8 percent | MIL-I-49428 section 3.6.18 | [P] |
| MTF at 15/25 lp/mm, MX-10160B/GS | 61/38 percent | Litton B datasheet; MX-10160-GS section 3.4 | [P] |
| SNR | >=16.2 | MIL-I-49428 section 3.6.11 | [P] |
| Output brightness uniformity | <=3:1 at 2856 K | MIL-I-49428 section 3.6.13 | [P] |
| EBI at room temperature | <=2.5e-11 phot | MIL-I-49428 section 3.6.7 | [P] |
| Photocathode sensitivity | >=1000 uA/lm | MIL-I-49428 section 3.6.1 | [P] |
| Luminance gain | 20000-35000 fL/fc at 2e-6 fc | MIL-I-49428 Table II | [P] |
| Phosphor persistence, P20/P43/P45 | ~60 / ~2.6 / ~2.6 ms | Proxivision PR-0069E-02 via the repo comment `fnc_applyNVGTubeModel.sqf:862-865` | [PROJECT] |
| Pincushion distortion percent per generation | - | Not in any source read | [UNSOURCED] |
| Reticulation modulation depth | - | Not in any source read | [UNSOURCED] |
| Scintillation index vs flux | - | Not in any source read | [UNSOURCED] |
| AGC pole or time constant | - | Papers located (Br J Radiol 74(886):938, 2001; IEEE EDM 2013) but not read | [UNSOURCED] |
| Numeric auto-gate open, close and recovery constants | - | Not in any source read. Section 3.6.22 is persistence, not gate recovery | [UNSOURCED] |
| MIL-PRF-49428 revision | - | Only the 1989 MIL-I-49428 is in hand. The code's "49428F" is not verified | [UNVERIFIED] |
| Veiling glare band 2-5 percent | - | Only the 2.13 percent low end is sourced | [UNSOURCED] |
| ColorCorrections non-zero weight | - | Repo comment only. Not on the wiki | [UNSOURCED] |
| Blinding envelope constants (whiteMax, blackMin, contrastLoss) | 1.6/1.4/1.0/1.0, 1.0/1.0/0.15/0.10, 0.6/0.4 | Modelling choice, bounded by the auto-gate literature, no numeric source | [UNSOURCED] |
| AGC breathing oscillation frequency | 3.0 rad/s | Modelling choice. The section 3.6.6 tolerance bounds the amplitude, not the frequency | [UNSOURCED] |
| Scintillation coefficients | 0.55 / 0.25 / 0.5 / 0.1 lux reference | Modelling choice, no source | [UNSOURCED] |
| Blemish per-tier base array | 0.85 / 0.55 / 0.30 / 0.15 | Ordering from the MIL-I-49428 Table III density. The normalised alpha is a modelling choice | [UNSOURCED] |
| FPN mottle spatial realisation | - | The amplitude envelope is section 3.6.12. The spatial pattern is a modelling choice | [UNSOURCED] |
