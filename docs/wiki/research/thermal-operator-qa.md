# Thermal Model Operator QA

This checklist holds the operator-only rows for the `aee_thermal` layer. Each
row gives the exact steps, the log path and the expected observation. A
headless probe cannot read pixels, so the rendered look is operator-only.
Rows marked NEEDS OPERATOR GAME RUN are not verified in this work.

The log path is the report file of the active Arma 3 profile. On Windows the
default is `%LOCALAPPDATA%\Arma 3\<profile>.rpt`. On Linux it is
`~/.local/share/Arma 3/<profile>.rpt`. The `-profiles=` launch option moves
the root. Read the newest `.rpt` after each run.

## What the model computes

The model computes the apparent band radiance that a thermal sensor reads. It
integrates the Planck function over one detector band, applies the atmospheric
transmission, and mixes the emitted, reflected and path terms (the FLIR
three-term measurement equation). The display then applies a degradation
factor and a sensor noise term.

The model carries two bands. The LWIR band is 8-14 um. The MWIR band is
3-5 um. The band is a per-device corpus value, because a cooled detector can
work in either band.

| Device class | Band |
|---|---|
| Uncooled microbolometer (VOx) | LWIR 8-14 um |
| Cooled InSb | MWIR 3-5 um |
| Cooled MCT Catherine-MP LW | LWIR 8-14 um |
| Cooled MCT Sophie Ultima, FLIR Recon V, Safran JIM LR | MWIR 3-5 um |

The band comes from the detector class in the device library. It is not
guessed from the `cooled` flag.

## Settings an operator can change

The thermal settings live under the module settings tree. The exact keys and
defaults follow.

| Setting key | Category | Default | Purpose |
|---|---|---|---|
| `aee_thermal_thermalPolarity` | AEE Thermal > Display | White hot | White hot or black hot palette |
| `aee_thermal_thermalBaseChannel` | AEE Thermal > Display | Vanilla TI | Draw on the engine TI channel or the DTV channel |
| `aee_thermal_thermalDisplayMode` | AEE Thermal > Display | Automatic (AGC) | Automatic, manual or per-object display window |
| `aee_thermal_thermalPalette` | AEE Thermal > Display | Ember | Palette |
| `aee_thermal_thermalManualMinC` | AEE Thermal > Display | -40 | Manual window minimum in C |
| `aee_thermal_thermalManualMaxC` | AEE Thermal > Display | 120 | Manual window maximum in C |
| `aee_thermal_thermalWetDistortion` | AEE Thermal > Display | 0.08 | Rain-on-lens blur ceiling |
| `aee_thermal_thermalPixelation` | AEE Thermal > Display | false | Quantise to the device resolution |
| `aee_thermal_thermalFPN` | AEE Thermal > Display | true | Fixed-pattern-noise material |
| `aee_thermal_thermalPPEffects` | AEE Thermal > Display | true | Thermal post-process kill switch |
| `aee_thermal_repaintHz` | AEE Thermal > Display | 4 | Repaint rate in hertz |
| `aee_thermal_thermalImperfectionsEnabled` | AEE Thermal > Sensor | true | NUC drift, temporal noise, AGC hunt, hot bloom |
| `aee_thermal_thermalTemporalNoise` | AEE Thermal > Sensor | 1 | Temporal-noise scale |
| `aee_thermal_thermalAgcHunt` | AEE Thermal > Sensor | 0.05 | AGC hunt amplitude |
| `aee_thermal_thermalAgcHuntPeriod` | AEE Thermal > Sensor | 4 | AGC hunt period in seconds |
| `aee_thermal_thermalNucDrift` | AEE Thermal > Sensor | 0.15 | NUC drift amplitude |
| `aee_thermal_thermalHotBloom` | AEE Thermal > Sensor | 0.08 | Hot-source bloom |
| `aee_thermal_activeIR` | AEE Thermal > Sensor | false | Active-IR illuminator, client-local |
| `aee_thermal_objectScanInterval` | AEE Thermal > Solver | 30 | Object-temperature scan interval in seconds |
| `aee_thermal_thermalDebug` | AEE Debug > Thermal | false | Thermal debug flag |
| `aee_thermal_logDebug` | AEE Debug > Thermal | false | Thermal DEBUG and TRACE lines |

The fusion switches are separate. They are `aee_thermal_fusionAlwaysOn`,
`aee_thermal_fusionFovFrame`, `aee_thermal_fusionOutline` and
`aee_thermal_fusionSolidFill` under **AEE Experimental > Fusion**, and
`aee_thermal_fusionHud` under **AEE HUD > Displays**.

## A cooled MWIR sight by day

Steps. Hold a cooled MWIR device (for example a Sophie Ultima class). Face a
sunlit scene.

Log path. The active profile `.rpt`, thermal band radiance line.

Expected. The scene carries a reflected-sunlight component. The sunlit
surfaces read warmer than a shadowed surface at the same physical
temperature. NEEDS OPERATOR GAME RUN.

## A cooled MWIR sight at night

Steps. Same device, after dark.

Log path. The active profile `.rpt`, thermal band radiance line.

Expected. The reflected-solar term is zero. The scene reads like an LWIR scene
at the same conditions. NEEDS OPERATOR GAME RUN.

## Night cold-sky contrast

Steps. Use an LWIR device on a clear night at low humidity. Look at bare
metal. Raise the humidity or the overcast.

Log path. The active profile `.rpt`, band sky line.

Expected. The band sky is well below the air temperature and the metal reads
dark. A higher humidity or overcast raises the band sky. NEEDS OPERATOR GAME
RUN.

## Thermal crossover at dawn

Steps. Watch the ground and an object across dawn. Turn on
`aee_thermal_thermalDebug`.

Log path. The active profile `.rpt`, crossover surface temperature line.

Expected. The ground surface temperature follows the four-layer node stack,
so the crossover time moves with the modelled ground and not a coarse switch.
NEEDS OPERATOR GAME RUN.

## A wet surface

Steps. Let rain wet the ground. Compare a wet surface with the same dry
surface.

Log path. The active profile `.rpt`, effective emissivity line.

Expected. The wet surface emissivity rises toward 0.96 and its apparent
radiance follows. NEEDS OPERATOR GAME RUN.

## The active-IR illuminator

Steps. Enable `aee_thermal_activeIR` under AEE Thermal > Sensor. View the
operator with an IR optic, then with the unaided eye.

Log path. The active profile `.rpt`, active IR line.

Expected. The IR optic sees the illuminator. The unaided eye does not. The
light and the particle are gone when the setting is off. NEEDS OPERATOR GAME
RUN.

## AI IR detection

Steps. Let an AI vehicle with an IR sensor acquire a hot vehicle.

Log path. None.

Expected. Acquisition follows the heat model and the declared IR scan ranges.
This is separate from the rendered image. NEEDS OPERATOR GAME RUN.

## The honest ceiling

The following limits are real and are not defects.

- The MWIR clear-air transmission is ceilinged at 1. No sourced closed form
  for the 3-5 um band exists in the repository, so the clear-air term returns
  1. Fog and rain still attenuate.
- Terrain, vegetation and rock heat are engine-baked. Only the existing second
  sun reaches them. AEE ships no texture and cannot repaint an arbitrary
  object.
- The native thermal renderer is compiled. The moddable path for a live image
  remains the display track. The fusion track is the moddable path for a fused
  image.
- A headless probe cannot read pixels. A log can show a computed value. It
  cannot show the rendered look.
- The atmospheric path radiance stays isothermal, so a long slant path or a
  temperature inversion is out of the model.
- The AI IR detection model is separate from the rendered image. It reads the
  real heat signature and not pixels.

## Non-goals

- No fake thermal image. No whole-object emissive re-skin, no second sun as
  the model, and no two-dimensional hot-body overlay.
- No copied mod content. Every idea is re-implemented as AEE code.
- No invented constant. Every value is sourced, derived with its formula, or
  marked UNSOURCED.
- No terrain, vegetation or rock repaint. Those are engine-baked.
- No runtime change to the engine render pass. The levers are load-time
  config and runtime commands only.
