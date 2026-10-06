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
| green colorize | [1.3, 1.2, 0.0, 0.9] | ACE3 green preset ⚠️ red-dominant (r > g, b = 0): renders amber, not green |
| green weight | [6, 1, 1, 0] | ACE3 green weight ⚠️ red-weighted, dims a green image |
| P43 green (used) | [0.1, 1.3, 0.0, 0.9] | P43 Gd2O2S:Tb, 545 nm (Exosens PR-0056E-03): green-dominant ✅ |
| P43 weight (used) | [0.299, 0.587, 0.114, 0] | BIKI ColorCorrections default: green-dominant ✅ |
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
| phosphorTint [0.1,1.3,0,0.9] | colorize | P43 green, 545 nm (Exosens PR-0056E-03) | ✅ green-dominant |
| nvgWeight [0.299,0.587,0.114,0] | weight | BIKI ColorCorrections default | ✅ green-dominant |
| chromaStrength 0.004 | ChromAberration | WIKI: below 0.005 default | ✅ in range |
| vigStrength [0.003,0.003,0.06,0.06] | RadialBlur | WIKI range | ✅ in range |
| bloomBase/Scale 0.03 | DynamicBlur | ACE3 band | ⚠️ below floor |

### GEN2
| Value | Used | Source | Status |
|---|---|---|---|
| sensitivity 550 µA/lm | gain | DS: multialkali Gen2 | ✅ datasheet |
| noiseFloor 0.08 | noise | DS | ⚠️ judgment |
| mtf15 0.45 | contrast | DS: 47-54 lp/mm → ~45% | ✅ derived |
| phosphorTint [0.1,1.3,0,0.9] | colorize | P43 green, 545 nm (Exosens PR-0056E-03) | ✅ green-dominant |
| nvgWeight [0.299,0.587,0.114,0] | weight | BIKI ColorCorrections default | ✅ green-dominant |
| chromaStrength 0.006 | ChromAberration | WIKI: slightly above default | ✅ in range |
| vigStrength [0.004,0.004,0.06,0.06] | RadialBlur | WIKI range | ✅ in range |
| bloomBase/Scale 0.04 | DynamicBlur | ACE3 band | ⚠️ below floor |

### GEN1
| Value | Used | Source | Status |
|---|---|---|---|
| sensitivity 250 µA/lm | gain | DS: S-25 multialkali | ✅ datasheet |
| noiseFloor 0.15 | noise | DS | ⚠️ judgment |
| mtf15 0.30 | contrast | DS: 30-40 lp/mm → ~30% | ✅ derived |
| phosphorTint [0.4,1.3,0,0.9] | colorize | P20 yellow-green, ~550 nm (Exosens PR-0056E-03) | ✅ green-dominant |
| nvgWeight [0.299,0.587,0.114,0] | weight | BIKI ColorCorrections default | ✅ green-dominant |
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
2. **Blowout cone (20° half-angle)**.  Derived: AN/AVS-9 FOV is 40°
   circular (DTIC ADA426388, NASA 20030063076, Elbit datasheet), so the
   gate cone matches the tube FOV.  Detection range 150m remains calibration.
3. **Grain intensity scale** (noise 0.03..1 → 0..1).  Physics gives the
   shape; the magnitude is engine-tuned.
4. **PHOTON_SCALE** (single constant, 500).  Converts µA/lm
   photocathode sensitivity to a detected-photon count (cathode area × QE
   × integration time ÷ electron charge).  ONE calibration knob, not four
   per-tier magic numbers.
5. **setAperture 15** (eye accommodation, night).  Derived: BIS wiki
   calibration (50 = daylight outdoor, 30 = indoor, <20 = night).
   A3TI-proven 15.  NOTE: setAperture is light intake, NOT depth of field.
   True player-view DoF is not scriptable (camSetFocus is camera-only);
   RadialBlur approximates focus behaviour.
6. **Fiber cell counts** (28/42).  SCHOTT datasheet bundle sizes, mapped
   to screen pixels, so the mapping constant is calibration.

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

## Thermal contrast (fnc_calculateThermalContrast.sqf)

The kernel is a display-degradation factor with no base gain and no weather
term of its own. Atmospheric degradation is modelled once, in
fnc_calculateAtmosphericTransmission.

| Value | Used | Source | Status |
|---|---|---|---|
| contrast base 1.0 | no display gain | engine renders the native image | ✅ derived |
| heat threshold 35 / span 10 / factor 0.7 | gradient flatten | none | ⚠️ UNSOURCED |
| cold threshold 5 / factor 1.2 | gap widen | none | ⚠️ UNSOURCED |
| rain × 0.4 / fog × 0.6 / humidity × 0.3 | removed | double-counted transmission | removed |

## Thermal noise (fnc_calculateThermalNoise.sqf)

The noise floor is a pure kernel driven by a REAL sensor-to-target range. It
replaced the engine view-distance proxy.

| Value | Used | Source | Status |
|---|---|---|---|
| range 1000 m fallback | no-target range | none (device corpus holds no detection range) | ⚠️ UNSOURCED |
| 640 detector reference | resolution scaling | uncooled reference class | ✅ derived |
| humidity coefficient 0.5 | water-vapour noise | none | ⚠️ UNSOURCED |
| range squared | path noise growth | scintillation/absorption | ⚠️ UNSOURCED |

## Wet-surface emissivity (fnc_getEffectiveEmissivity.sqf)

| Value | Used | Source | Status |
|---|---|---|---|
| WATER_EPS 0.96 | liquid-water LWIR emissivity | Incropera; Hale and Querry 1973 DOI 10.1364/AO.12.000555; Downing and Williams 1975 DOI 10.1029/JC080i012p01656 | ✅ sourced |
| linear film blend | wetness interpolation | convergence only: Lavielle et al. 2024 DOI 10.1002/adfm.202403316 | ⚠️ UNSOURCED |

## Detector bands (fnc_resolveThermalBand.sqf)

The band is a per-device corpus field, not a derived flag.  Both edge pairs
are declared, not fitted.  An unknown token returns the LWIR pair.

| Value | Used | Source | Status |
|---|---|---|---|
| LWIR band 8e-6 / 14e-6 m | band edges | detector class in sensor-device-library.md | ✅ verified |
| MWIR band 3e-6 / 5e-6 m | band edges | cooled InSb and cooled MWIR MCT detector classes in sensor-device-library.md | ✅ verified |

## Planck band integral (fnc_planckBandRadiance.sqf)

| Value | Used | Source | Status |
|---|---|---|---|
| C 2.779416505e-9 W/m2/sr/K4 | radiance scale | CODATA 2022 (2 k^4 / h^3 c^2) | ✅ verified |
| c2 1.438776877e-2 m K | band exponent | CODATA 2022 (h c / k) | ✅ verified |
| domain guard 100..10000 K | numerical bound | admits the solar temperature 5772 K | ✅ derived |

## Band sky temperature (fnc_calculateSkyRadiance.sqf)

The fixed 35 K offset is retired.  The band emissivity is the exact Planck
radiance ratio at the depressed temperature, not the Stefan-Boltzmann
quartic.

| Value | Used | Source | Status |
|---|---|---|---|
| Magnus 6.112 / 17.67 / 243.5 | water-vapour partial pressure | Bolton 1980 | ✅ verified |
| full-spectrum eps 0.70 + 5.95e-5 e exp(1500/T_K) | clear-sky emissivity | Idso 1981, Water Resources Research 17(2):295-304, DOI 10.1029/WR017i002p00295 | ✅ verified |
| band depression 45 K at eHPa <= 4 | measured band envelope | Tebo 1965, Effective Clear Sky Temperatures in the 8- to 14-Micron Band | ✅ derived |
| band depression 21 K at eHPa >= 15 | measured band envelope | Tebo 1965 | ✅ derived |
| log(eHPa) interpolation between 4 and 15 hPa | intermediate depression | none | ⚠️ UNSOURCED |
| band emissivity B_band(T_sky) / B_band(T_air) | exact Planck radiance ratio | derived-from-measurement (Tebo 1965 envelope, Planck function) | ✅ derived |
| overcast blend (1 - overcast) | cloud fills the window | Tebo 1965 envelope limit, no cloud model | ⚠️ UNSOURCED |
| bisection 40 iterations, T in 1..T_air | band sky inversion | convergence bound, not physics | ✅ derived |

## Reflected-solar band radiance (fnc_calculateReflectedSolarBand.sqf)

MWIR only.  Zero for LWIR and zero when the sun is at or below the horizon.
The whole term is derived from the Planck function and the solar constant.

| Value | Used | Source | Status |
|---|---|---|---|
| T_sun 5772 K | solar effective temperature | IAU 2015 Resolution B3 nominal solar effective temperature | ✅ verified |
| R_sun 6.957e8 m, AU 1.495978707e11 m | top-of-atmosphere geometry | IAU 2015 Resolution B3 nominal values | ✅ verified |
| E_sunBand ~21.7 W/m2 (MWIR) | band irradiance | derived: pi B_band(T_sun) (R_sun / AU)^2 | ✅ derived |
| W_solar = (1-eps) E_sunBand sin(elev) / pi | reflected radiance | derived (Lambertian surface, Kirchhoff reflectance) | ✅ derived |

## Band atmospheric transmission (fnc_calculateAtmosphericTransmission.sqf)

The LWIR path is Minkina and Klecha 2016 and is unchanged.

| Value | Used | Source | Status |
|---|---|---|---|
| MWIR clear-air extinction 0 (transmission 1) | clear-air ceiling | no machine-readable 2-5 um band transmittance curve is held | ⚠️ UNSOURCED |

## Active-IR illuminator (ir/fnc_startActiveIR.sqf)

| Value | Used | Source | Status |
|---|---|---|---|
| #lightreflector with setLightIR true | IR-only illuminator | none (workshop idea re-implemented) | ⚠️ UNSOURCED |
| ambient 0.02, colour 0.15, brightness 0.25 | light tuning | none | ⚠️ UNSOURCED |
| attach offset [0, 0, 0.1] m | light placement | none | ⚠️ UNSOURCED |

## Post-process priority ladder (fnc_applyThermalVision.sqf)

Each priority is one engine band.  The union of every AEE handle is globally
unique, enforced by test_thermal_optics.

| Value | Used | Source | Status |
|---|---|---|---|
| WetDistortion 305 | priority | workshop 3753145363 proven band | ✅ derived |
| ChromAberration 205 | priority | A3TI and MKK proven band | ✅ derived |
| DynamicBlur 505 | priority | proven defocus band | ✅ derived |
| RadialBlur 1000 | priority | MKK proven value | ✅ derived |
| FilmGrain 2000 | priority | A3TI variant; fusion holds 2005 | ✅ derived |
| ColorCorrections 2500 | priority | proven grade band; fusion holds 2505 | ✅ derived |
| ColorInversion 2510 | priority | A3TI 2501 and MKK 2510 proven BHOT band | ✅ derived |
| Resolution 3000 | priority | A3TI proven value | ✅ derived |

## Per-optic thermal config (generated/ThermalOptics.hpp)

| Value | Used | Source | Status |
|---|---|---|---|
| thermalMode[] {0,1} | WHOT and BHOT palette pair | engine-minimum pair, engine-thermal-mechanisms.md | ✅ verified |
| thermalNoise[] {netd_c} | detector noise | corpus field netd_c | ✅ derived |
| thermalResolution[] {resX, resY} | detector pixel array | corpus fields resolution_x and resolution_y | ✅ derived |

## Illuminance layer (fnc_calculateIlluminance.sqf)

The shared light-data source consumed by NVG, thermal and glare.  Two
engine commands feed it, verified by docker probe (PHASE12):

| Value | Source | Engine proof |
|---|---|---|
| lightDirection / azimuth / elevation | `getLighting` (no-arg) | docker probe: `[color, 84987.1, [0.0255,0.472,-0.881], 0]`, 4 elements on dedicated server |
| starsVisibility | `getLighting` (no-arg) | same probe |
| ambient lux (moon model) | moonIntensity/overcast/rain | physics model, validated |
| dynamic lux (client) | `getLightingAt _unit` | probe: works on a UNIT, returns [] on a logic |

Engine caveats discovered by probe (documented, not guessed):
- `getLighting` ambientBrightness is FROZEN on a headless server (lighting
  advances only per client camera), and it is NOT usable as the lux source there.
- `getLightingAt` requires a real unit, and is client-NV dependent
  (BIS tracker T156930).
- The engine vector points FROM the light: elevation is negated for the
  sun's true elevation (probe z=-0.881 → sun ≈ +61.8°).

Glare now consumes the engine sun vector (lightAzimuth/lightElevation)
with a dayTime-sine fallback if the illuminance layer has not run yet.

## Cross-module consistency producers

The consistency harness (INV-1 to INV-5) reads these published values.  Each
one states its grade.

| Value | Used | Source | Grade |
|---|---|---|---|
| `aee_thermal_humanCoreTempC` | body-temperature invariant INV-4 | Gagge 1986 body-temperature weighting, 0.1 skin + 0.9 core.  Published from `fnc_solveTwoNodeSelection.sqf` for a human selection only. | derived |
| `aee_core_coreBodyTemp` | body-temperature invariant INV-4; KAT circulation | Physiology heat balance in `fnc_coreBodyTemp.sqf`.  The 37 C baseline is sourced (normal resting human core temperature).  The heat threshold (28 C WBGT), the heat gain (0.05), the cold threshold (10 C wind chill), the cold gain (0.10) and the hypothermia loss (4.0) are UNSOURCED modelling choices. | baseline sourced; coefficients UNSOURCED |
| `aee_thermal_skyBandTempC` | solar/sky invariant INV-5 | The Tebo 1965 8-14 um band envelope applied by `fnc_calculateSkyRadiance.sqf`; published from `fnc_calculateBandRadiance.sqf`. | derived-from-measurement |

## Ground node stack shape (aee_thermal_groundNodeStack)

The producer `fnc_calculateGroundNodeStack.sqf` publishes
`aee_thermal_groundNodeStack` as a HashMap, not a scalar.  The key is a
position grid cell and material (`floor(x/5)_floor(y/5)_<material>`) and the
value is a six-element array: the four layer temperatures at node depths
0.05 / 0.25 / 0.70 / 1.50 m (C), the deep-soil TBOT anchor (C), and the last
advance tick (`diag_tickTime`).  A water position stores the same six values
all set to the water temperature, so one shape covers land and water.  The
stack has memory: a caller advances it by the real elapsed time since the
last advance, and later callers in the same tick read the same state.  The
consistency harness therefore reads the map, not a single number, and takes
the surface layer (index 0) as the ground-surface estimate for INV-2.  Its
Annex C row is added by task 18.

## MGRS and positioning constants

The aee-mgrs-and-positioning work adds the geographic anchor, the MGRS
kernels, the GNSS kernels and the tracker projector. Sources:
- **TM8358.2**: DMA TM 8358.2, "The Universal Grids: UTM and UPS", Ed.1 1989
- **TM8358.1**: DMA TM 8358.1, the MGRS lettering figures
- **MGRS2009**: NGA MGRS guidance, Modified February 2009
- **WGS84**: NIMA TR8350.2, the WGS84 ellipsoid
- **SPS**: GPS Standard Positioning Service Performance Standard, 5th ed, April 2020 (gps.gov)

### UTM projection (fnc_latLonToUtm.sqf, fnc_utmToLatLon.sqf)

| Value | Used | Source | Status |
|---|---|---|---|
| a 6378137 m, 1/f 298.257223563 | WGS84 ellipsoid | WGS84 (NIMA TR8350.2) | ✅ sourced |
| k0 0.9996 | UTM scale factor | TM8358.2 ch.2-3 | ✅ sourced |
| false easting 500000 m | UTM easting origin | TM8358.2 ch.2-3 | ✅ sourced |
| false northing 10000000 m south | UTM southern origin | TM8358.2 ch.2-3 | ✅ sourced |
| forward and inverse transverse Mercator series | UTM projection | TM8358.2 ch.2-3 | ✅ sourced |
| zone number from longitude | UTM zone | TM8358.2 | ✅ sourced |
| zone clamp 1..60 | valid zone bound | UTM definition | ✅ derived |

### MGRS letter tables (fnc_formatMgrs.sqf, fnc_parseMgrs.sqf)

The tables live in the generated file `addons/core/data/mgrs_tables.sqf`.

| Value | Used | Source | Status |
|---|---|---|---|
| latitude band letters, 8 degree steps | Grid Zone Designation | MGRS2009; TM8358.1 figure | ✅ sourced |
| band X 12 degrees high, north to 84 | band set | MGRS2009 | ✅ sourced |
| column letter sets, 3 sets of 8 | 100 km square column | MGRS2009; TM8358.1 | ✅ sourced |
| row letters, 20 rows | 100 km square row | MGRS2009; TM8358.1 | ✅ sourced |
| even-zone row offset 5 | row cycle | MGRS2009; TM8358.1 | ✅ sourced |
| digits truncated, south-west corner | MGRS reference | MGRS2009 | ✅ sourced |
| 2000000 m northing cycle | southern hemisphere cycle | MGRS2009 | ✅ sourced |
| precision one of 2, 4, 6, 8, 10 | valid digit count | MGRS2009 | ✅ sourced |

### World-to-MGRS local projection (fnc_worldToMgrs.sqf, fnc_mgrsToWorld.sqf)

The anchor box maps the world square linearly to the geographic box. When the
anchor has no usable box, the fallback is a local tangent plane at the anchor
centre. The tangent plane is an approximation, not a projection.

| Value | Used | Source | Status |
|---|---|---|---|
| WGS84 a 6378137 m, 1/f 298.257223563 | meridian radius of curvature | WGS84 | ✅ sourced |
| M = a(1-e2)/(1-e2 sin2)^1.5 | metres per degree of latitude | WGS84 ellipsoid | ✅ derived |
| longitude scale cos(latitude) | metres per degree of longitude | local tangent plane | ✅ derived |
| linear anchor-box mapping | world square to geographic box | the design choice | ⚠️ UNSOURCED approximation |
| tangent-plane fallback | world position to lat/lon | the design choice | ⚠️ UNSOURCED approximation |

### GNSS error ellipse (fnc_gnssErrorEllipse.sqf)

| Value | Used | Source | Status |
|---|---|---|---|
| UERE 3.6 m RMS | 1-sigma range error | SPS App. A.4 | ✅ sourced |
| horizontal 8 m, vertical 13 m at 95 percent | accuracy standard | SPS App. A.4 | ✅ sourced |
| 13/8 = 1.625 | vertical-to-horizontal 1-sigma ratio | derived from SPS | ✅ derived |
| sigma = DOP x UERE | 1-sigma horizontal error | SPS App. A.8.2 | ✅ sourced |
| R95 = 2.0 x DRMS | 2DRMS radius | SPS App. A.8.2 | ✅ sourced |
| atmosphere gain 0.5 per index | sigma gain | none | ⚠️ UNSOURCED |
| canopy gain 1.0 per fraction | sigma gain | none | ⚠️ UNSOURCED |
| urban gain 1.5 per fraction | sigma gain | none | ⚠️ UNSOURCED |
| urban anisotropy 2 | east-west axis stretch | none | ⚠️ UNSOURCED |
| jam gain 20, on jammer^1.5 | sigma gain | none | ⚠️ UNSOURCED |
| receiver max penalty 2 | sigma gain | none | ⚠️ UNSOURCED |
| CEP coefficient 0.589 | elliptical CEP | none | ⚠️ UNSOURCED |

### GNSS fix continuity (fnc_gnssFixState.sqf)

| Value | Used | Source | Status |
|---|---|---|---|
| availability then a non-zero re-acquisition | continuity mechanism | SPS s.3.6 and App. A.8 | ✅ sourced |
| effective-signal acquire floor 0.3 | fix gate | none | ⚠️ UNSOURCED |
| re-acquisition rate 0.25 per second | recovery ramp | none | ⚠️ UNSOURCED |
| decay rate 1.0 per second | progress loss | none | ⚠️ UNSOURCED |
| jamming removes the received signal | effective signal | none | ⚠️ UNSOURCED |
| lag 2 m per second since the fix | lag offset | none | ⚠️ UNSOURCED |
| lag 40 m at zero progress | lag offset | none | ⚠️ UNSOURCED |
| stutter envelope 0.5 | jitter amplitude | none | ⚠️ UNSOURCED |

### Datalink falloff (fnc_datalinkState.sqf)

| Value | Used | Source | Status |
|---|---|---|---|
| FSPL = 20log10(d) + 20log10(f) - 147.55 | range falloff shape | Friis, reused from the radio module | ✅ derived |
| reference range 5000 m | usable range | none | ⚠️ UNSOURCED |
| reference carrier 3e8 Hz | falloff | none | ⚠️ UNSOURCED |
| terrain range fraction 0.6 | range loss | none | ⚠️ UNSOURCED |
| urban range fraction 0.3 | range loss | none | ⚠️ UNSOURCED |
| jamming range fraction 0.9 | range loss | none | ⚠️ UNSOURCED |
| terrain loss 12 dB | signal loss | none | ⚠️ UNSOURCED |
| urban loss 6 dB | signal loss | none | ⚠️ UNSOURCED |
| jamming loss 30 dB | signal loss | none | ⚠️ UNSOURCED |
| base interval 1.0 s, reference bandwidth 100 | update interval | none | ⚠️ UNSOURCED |
| track age 30 s at zero signal | track age | none | ⚠️ UNSOURCED |
| added error 25 m at zero signal | position error | none | ⚠️ UNSOURCED |
| lost-link error penalty 15 m | position error | none | ⚠️ UNSOURCED |

### Tracker projection (fnc_trackerProject.sqf)

| Value | Used | Source | Status |
|---|---|---|---|
| error term = ellipse R95 + datalink error + fix lag | displacement magnitude | the three kernel outputs | ✅ derived |
| phase step 137.508 degrees, the golden angle | per-track bearing | the golden-angle constant | ⚠️ UNSOURCED mapping |
| displacement sum and bearing choice | displayed position | none | ⚠️ UNSOURCED mapping |

### Tracker driver (fnc_trackerUpdate.sqf)

| Value | Used | Source | Status |
|---|---|---|---|
| humidity to atmosphere index, humidity / 100, default 50 | ellipse atmosphere input | none | ⚠️ UNSOURCED |
| canopy probe height +40 m vertical ray | canopy mask | none | ⚠️ UNSOURCED |
| urban survey radius 50 m | urban mask | none | ⚠️ UNSOURCED |
| urban saturation 8 buildings | urban fraction cap | none | ⚠️ UNSOURCED |
| canopy signal gain 0.5 per fraction | effective signal | none | ⚠️ UNSOURCED |
| urban signal gain 0.3 per fraction | effective signal | none | ⚠️ UNSOURCED |
| DOP 1.0 | ellipse sigma | none | ⚠️ UNSOURCED |
| receiver quality 1.0 | ellipse sigma | none | ⚠️ UNSOURCED |

### Geographic anchor (fnc_buildGeoAnchor.sqf, fnc_getGeoAnchor.sqf)

| Value | Used | Source | Status |
|---|---|---|---|
| mapArea order [lonWest, latSouth, lonEast, latNorth] | anchor box | BIS `fn_posDegtoWorld.sqf` | ✅ verified |
| CfgWorlds latitude sign inverted, positive is south | anchor centre | BIS CfgWorlds convention | ✅ verified |
| fallback 40 N, 0 longitude | anchor without a box | the prior latitude reader fallback | ⚠️ UNSOURCED |
