# NVG/Thermal Sensor Value Audit

Every tunable value in the sensor pipeline, its source, and its
verification status.  Sources:
- **WIKI**: BIS wiki `Post_Process_Effects` parameter tables (ranges/defaults)
- **ACE3**: `addons/nightvision` source (ST_NVG_* constants, fnc_pfeh)
- **A3TI**: workshop 2041057379 (thermal improvement, fn_ppEffects.sqf)
- **DS**: tube datasheet (ITT/Elbit, Photonis, MIL-PRF-49428F)
- **JUDG**: engine calibration judgment call (documented, not physics-derivable)

Legend: ✅ verified against source · ⚠️ judgment call (documented)

## Effect parameter ranges (BIS wiki)

| Effect | Param | Wiki range | Wiki default |
|---|---|---|---|
| ColorCorrections | brightness | 0..2 | 1 |
| ColorCorrections | contrast | 0... | 1 |
| ColorCorrections | colorize a | 0..1 (0=orig, 1=B&W×color) | [1,1,1,1] |
| ColorCorrections | weight | 0..1 | [0.299,0.587,0.114,0] |
| FilmGrain | intensity | 0..1 | 0.005 |
| FilmGrain | sharpness | 1..20 | 1.25 |
| FilmGrain | grainSize | 1..8 | 2.01 |
| FilmGrain | monochromatic | 0=mono, other=colour | 0 |
| DynamicBlur | value | 0... | 0 |
| RadialBlur | powerX/powerY | 0... | 0.01 |
| RadialBlur | offsetX/offsetY | 0... | 0.06 |
| ChromAberration | powerX/powerY | 0... | 0.005 |
| ChromAberration | aspectCorrection | bool | false |
| ColorInversion | R/G/B | 0..1 | 0 |

## Reference values (ACE3 nightvision, fnc_pfeh.sqf)

| Constant | ACE3 value | Our use |
|---|---|---|
| ST_NVG_BRIGHT_MIN/MAX | 0.65 / 0.75 | brightness floor/ceiling reference |
| ST_NVG_CONTRAST_MIN/MAX | 0.4 / 0.8 | contrast reference band |
| ST_NVG_GRAIN_MIN/MAX | 2.25 / 2.7 | grainSize band ✅ |
| ST_NVG_NOISESHARPNESS_MIN/MAX | 1.2 / 1.0 | sharpness band ✅ |
| ST_NVG_NOISEINTENSITY_MIN/MAX | 0.4 / 0.55 | grain intensity reference |
| green colorize | [1.3, 1.2, 0.0, 0.9] | GEN2/3 tint ✅ (exact match) |
| green weight | [6, 1, 1, 0] | GEN2/3 weight ✅ (exact match) |
| white colorize | [1.1, 0.8, 1.9, 0.9] | PVS-31 tint ✅ (exact match) |
| white weight | [1, 1, 6, 0] | PVS-31 weight ✅ (exact match) |

## Per-tier NVG values (fnc_applyNVGTubeModel.sqf)

### PVS-31
| Value | Used | Source | Status |
|---|---|---|---|
| sensitivity 2000 µA/lm | gain = sens/(lux+1) | DS: filmless GaAs (L3Harris/Photonis 4G) | ✅ datasheet |
| noiseFloor 0.03 | noise floor | DS: excellent SNR | ⚠️ magnitude judgment |
| mtf15 0.65 | contrast | DS: 64-81 lp/mm → ~65% MTF | ✅ derived |
| phosphorTint [1.1,0.8,1.9,0.9] | colorize | ACE3 white preset | ✅ exact |
| nvgWeight [1,1,6,0] | weight | ACE3 white preset | ✅ exact |
| chromaStrength 0.002 | ChromAberration | WIKI default 0.005, below doubling | ✅ in range |
| vigStrength [0.0025,0.0025,0.06,0.06] | RadialBlur | WIKI: power 0.01, offset 0.06 | ✅ in range |
| bloomBase/Scale 0.02 | DynamicBlur | ACE3 0.05-0.11 band | ⚠️ below ACE3 floor |

### GEN3
| Value | Used | Source | Status |
|---|---|---|---|
| sensitivity 1100 µA/lm | gain | DS: GaAs (Photonis ~700-1200) | ✅ datasheet |
| noiseFloor 0.04 | noise | DS | ⚠️ judgment |
| mtf15 0.61 | contrast | DS: Elbit MX-10160 61% | ✅ derived |
| phosphorTint [1.3,1.2,0,0.9] | colorize | ACE3 green preset | ✅ exact |
| nvgWeight [6,1,1,0] | weight | ACE3 green preset | ✅ exact |
| chromaStrength 0.004 | ChromAberration | WIKI: below 0.005 default | ✅ in range |
| vigStrength [0.003,0.003,0.06,0.06] | RadialBlur | WIKI range | ✅ in range |
| bloomBase/Scale 0.03 | DynamicBlur | ACE3 band | ⚠️ below floor |

### GEN2
| Value | Used | Source | Status |
|---|---|---|---|
| sensitivity 550 µA/lm | gain | DS: multialkali Gen2 | ✅ datasheet |
| noiseFloor 0.08 | noise | DS | ⚠️ judgment |
| mtf15 0.45 | contrast | DS: 47-54 lp/mm → ~45% | ✅ derived |
| phosphorTint [1.3,1.2,0,0.9] | colorize | ACE3 green preset | ✅ exact |
| nvgWeight [6,1,1,0] | weight | ACE3 green preset | ✅ exact |
| chromaStrength 0.006 | ChromAberration | WIKI: slightly above default | ✅ in range |
| vigStrength [0.004,0.004,0.06,0.06] | RadialBlur | WIKI range | ✅ in range |
| bloomBase/Scale 0.04 | DynamicBlur | ACE3 band | ⚠️ below floor |

### GEN1
| Value | Used | Source | Status |
|---|---|---|---|
| sensitivity 250 µA/lm | gain | DS: S-25 multialkali | ✅ datasheet |
| noiseFloor 0.15 | noise | DS | ⚠️ judgment |
| mtf15 0.30 | contrast | DS: 30-40 lp/mm → ~30% | ✅ derived |
| phosphorTint [1.4,1.3,0,0.9] | colorize | ACE3 green, warmer (P20) | ⚠️ derived from ACE3 |
| nvgWeight [6,1,1,0] | weight | ACE3 green preset | ✅ exact |
| chromaStrength 0.008 | ChromAberration | WIKI: above default, below doubling | ✅ in range |
| vigStrength [0.005,0.005,0.06,0.06] | RadialBlur | WIKI range | ✅ in range |
| bloomBase/Scale 0.05 | DynamicBlur | ACE3 band | ✅ in band |

## Physics formulas (validated in validate_sensors.py)

| Formula | Check | Status |
|---|---|---|
| gain = sensitivity/(lux+1) | AGC inverse-lux | ✅ |
| gain ratio over moon range | ratio formula | ✅ |
| noise = floor + (1-floor)×1/√(N+1) | Poisson sqrt(N) | ✅ |
| temp gain piecewise 0.7/1.0/0.85 | MIL-PRF-49428F | ✅ |
| brightness = linConv(lux, 0.65..1.0) | monotonic bounded | ✅ |
| mtf = linConv(noise, mtf15, mtf15×0.55) | 55% degradation | ✅ |
| BSP: mtf × (1-blowout×0.4) | gating penalty | ✅ |
| noise clamp 0.03..1 | bounds | ✅ |

## Known judgment calls (not physics-derivable)

These are engine-calibration constants.  They cannot be derived from
physics alone because Arma's post-process parameters are relative
multipliers, not physical units.  Each is documented with its reference.

1. **Brightness magnitude** (0.65..1.0 band).  The wiki anchor is
   1.0 = unchanged; 0.65 is ACE3's proven floor.  The exact value at a
   given lux is calibration.
2. **Blowout cone (30°), range (150m)**.  Chosen thresholds, not derived.
3. **Grain intensity scale** (noise 0.03..1 → 0..1).  Physics gives the
   shape; the magnitude is engine-tuned.
4. **PHOTON_SCALE** (single constant, 500).  Converts µA/lm
   photocathode sensitivity to a detected-photon count (cathode area × QE
   × integration time ÷ electron charge).  ONE calibration knob, not four
   per-tier magic numbers.
5. **setAperture 20**.  A3TI uses 15-25; 20 is the midpoint.
6. **Fiber cell counts** (28/42).  SCHOTT datasheet bundle sizes, mapped
   to screen pixels — the mapping constant is calibration.

## Thermal values (fnc_applyThermalVision.sqf)

| Value | Used | Source | Status |
|---|---|---|---|
| brightness 0.55..1.0 | display gain | A3TI 1.16 default; our AGC model | ⚠️ judgment |
| contrast 0.35..1.15 | display contrast | A3TI 0.62 default | ⚠️ judgment |
| colorize [1,1,1,0] | no desaturation | A3TI [1,1,1,0] | ✅ exact |
| weight [0.299,0.587,0.114,0] | desaturation weights | WIKI default | ✅ exact |
| grain 0.08..0.6 | sensor noise | A3TI 0.5 default | ⚠️ judgment |
| blur 0..0.35 | IR scatter | A3TI 0.25 | ⚠️ judgment |
| crossover twilight <10° | isothermal gate | solar model | ✅ derived |