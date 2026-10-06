# ADR-020: Thermal realism - the second band, the sourced sky, and the engine-native surface

Status: Accepted

## Context

AEE computes a thermal apparent radiance for the optical path. The core is
correct and sourced. Four gaps remained, and one long-standing engine
question was unresolved.

The simulator integrated one band only, the LWIR 8-14 um window. The device
library classifies cooled InSb and cooled MCT sensors that work in the MWIR
3-5 um window, so a single band could not represent those devices honestly.

The band sky temperature was a fixed 35 K below air, and its comment cited
"Aase and Idso 1981". That paper does not exist. The correct full-spectrum
identity is Idso 1981.

The contrast kernel applied its own rain, fog and humidity multipliers. The
atmospheric path kernel already models that attenuation, so the display
applied it twice. The same kernel used the engine `viewDistance` as a proxy
for the sensor range.

Thermal crossover read a coarse `groundState` switch instead of the four-layer
ground node stack that AEE already computes.

The engine question was whether it renders the `StageTI` texture directly or
treats the texture channels as heat-source coefficients into a simulated
cooling model. The research file held the first answer and the BI Community
Wiki held the second.

## Decision

### The two bands

A detector band is a per-device corpus field, `lwir` (8-14 um) or `mwir`
(3-5 um). It is not derived from the `cooled` flag, because a cooled MCT
detector can work in either band. The device resolver tuple grows from six
entries to seven by appending the band, so every existing index stays valid.
A pure resolver kernel maps a band token to its two edge wavelengths. An
unknown token returns the LWIR pair, which is the sane default.

### The band Planck integral

The Planck band integral takes the two band edges as parameters. The default
pair reproduces the pre-change LWIR value bit for bit. A refused band, where
the first edge is not positive or the second edge is not greater than the
first, is refused rather than clamped silently.

### The band sky temperature

The fixed 35 K offset is replaced by a pure sky kernel. It takes the band, the
air temperature, the humidity and the overcast.

The water-vapour partial pressure uses the Magnus curve that the transmission
kernel already uses, from Bolton 1980. The full-spectrum clear-sky emissivity
uses Idso 1981, Water Resources Research 17(2):295-304, DOI
10.1029/WR017i002p00295.

The Idso 1981 band equation for 8-14 um is paywalled and could not be
obtained. The kernel therefore derives the band emissivity from the Tebo 1965
measured 8-14 um band envelope. A clear-sky depression of 45 K holds at a
partial pressure of 4 hPa or less and 21 K at 15 hPa or more, interpolated
linearly in the logarithm of the partial pressure. The band emissivity is the
ratio of the exact Planck band radiance at the depressed temperature to the
radiance at air temperature. This path is graded `derived-from-measurement`,
and the interpolation is marked `UNSOURCED` in the register. Both the band
emissivity and the old implied value sit near 0.60 at 15 C and 50 percent
humidity, so night cold-sky contrast does not regress.

Overcast blends the depression toward zero, because cloud fills the window.
The kernel then scales the Planck band radiance by the band emissivity and
inverts the Planck band integral by bisection. It does not use the
Stefan-Boltzmann total-power shortcut.

The wrong "Aase and Idso 1981" citation is removed. The correct identities are
Idso 1981 for the full spectrum and Tebo 1965 for the measured band range.
Aase and Idso 1978, Water Resources Research 14(4):623, covers the full
spectrum only and may be cited only as such.

### The MWIR reflected-solar term

A daytime MWIR scene is driven by reflected sunlight. The kernel computes the
Planck radiance at the adopted solar effective temperature of 5772 K,
converts it to band irradiance at the top of the atmosphere with the solar
radius and the astronomical unit, and forms the reflected radiance of an
opaque Lambertian surface. The term is added only for the MWIR band and only
when the sun is above the horizon. It is zero for the LWIR band and zero at
night, and its default is zero so every LWIR caller is bit-identical. The term
is graded `derived` from the Planck function and the solar constant. The
derived top-of-atmosphere MWIR band irradiance is about 21.7 W/m2.

### The band atmospheric transmission

The transmission kernel takes a band parameter. The LWIR path is unchanged,
including the Minkina and Klecha 2016 square-root form, the Roberts continuum,
the carbon-dioxide term, the Magnus curve and the fog and rain linear terms.

For MWIR, a declared model was to be fitted to the held NASA report. No
machine-readable transmittance curve could be extracted. Rather than invent
one, the MWIR clear-air extinction is set to zero, so the clear-air term
returns 1. The fog and rain linear terms remain. This limitation is marked
`UNSOURCED` and is stated as a ceiling.

### The contrast kernel

The three weather multipliers are deleted. The kernel is a display
degradation factor with a base of exactly 1.0, and the atmospheric degradation
lives once, in the transmission kernel. The extreme-heat and cold terms
remain, converted from absolute air temperature to the surface-to-air gap
where a gap is available. Every coefficient is marked `UNSOURCED`.

### The sensor range

The `viewDistance` proxy is deleted. A pure noise kernel takes the real target
range, the device NETD, the detector resolution and the humidity. The
per-selection callers pass the sensor-to-selection distance. Where no target
exists, the caller passes the device detection range from the corpus if it
holds one, else the declared default 1000 m, marked `UNSOURCED`.

### The crossover ground node stack

Thermal crossover reads the four-layer ground node stack and takes its surface
layer. The twilight gate and the timer are unchanged. The old `groundState`
switch remains only as a fallback when the stack returns empty, marked
`UNSOURCED`. The `aee_core_surfaceTemperature` write is kept, because the
precipitation-phase kernel reads it.

### The wet-surface emissivity

A pure kernel blends a dry emissivity toward the liquid-water value 0.96 as
the surface wetness rises from 0 to 1. The water value is sourced to liquid
water LWIR emissivity, Hale and Querry 1973, Applied Optics 12(3):555, DOI
10.1364/AO.12.000555, and Downing and Williams 1975, DOI
10.1029/JC080i012p01656. The film-coverage blend is a declared model, cited
to Lavielle et al. 2024, DOI 10.1002/adfm.202403316, and marked `UNSOURCED`.
The blend applies where the emissivity feeds emission or reflection. The dry
material registry is unchanged.

### The engine-native surface

The StageTI conflict is settled. The engine renders thermal from a
per-object simulated temperature model, not a direct texture blit. A
material's `class StageTI` texture channels are heat-source coefficients. R is
solar gain, G is active engine heat, B is moving-part heat and A is
metabolism. The config scalars `htMin` and `htMax` are the half-cooling times,
`afMax` and `mfMax` are the capped surface temperatures, and `mFact` and
`tBody` are the metabolism influence and surface temperature. The field
`thermalProperties` does not exist in the vanilla config.

The primary source is the BI Community Wiki page "Thermal Imaging Maps",
oldid 155895. A headless probe cannot read pixels, so the probe verifies the
resolved config keys and the command contract only.

AEE's levers follow. AEE declares the render heat keys `htMin`, `htMax`,
`afMax`, `mfMax`, `mFact` and `tBody` once, as load-time config. AEE declares
the AI IR keys `irTarget`, `irTargetSize`, `irScanRangeMin`, `irScanRangeMax`,
`irScanToEyeFactor` and `irScanGround` in its single `CfgVehicles` block,
mirroring the vanilla samples. These keys are load-time and drive the separate
AI IR detection model, which reads the real heat signature and not pixels. A
generated `CfgWeapons` block declares per-optic `thermalNoise[]`,
`thermalResolution[]` and `thermalMode[]` from the device corpus. The declared
`thermalMode[]` pair is {0,1}, the engine-minimum WHOT and BHOT set. The
corpus derives `thermalNoise[]` from the detector NETD and
`thermalResolution[]` from the detector pixel array.

An active-IR source uses a `#lightreflector` particle and a light with
`setLightIR true`, and its mechanism is marked `UNSOURCED`. A
`BettIR_Config` class declares AEE's thermal optics compatible with BettIR. A
pure runtime capability probe reads an optic's `visionMode[]` and
`thermalMode[]` and reports whether native thermal is supported.

The post-process handles adopt the proven per-type priority bands, so a
thermal handle and an NVG handle cannot share a priority. The thermal ladder
is WetDistortion 305, ChromAberration 205, DynamicBlur 505, RadialBlur 1000,
FilmGrain 2000, ColorCorrections 2500, ColorInversion 2510 and Resolution
3000. This is a deviation: the fusion track already holds FilmGrain 2005 and
ColorCorrections 2505, so the thermal track uses 2000 and 2500. The union of
every AEE handle stays globally unique.

The band and the new terms are threaded through every caller. Every declared
default remains the fallback, so a caller that cannot read a device still
computes the LWIR value.

## Alternatives rejected

- A whole-object emissive re-skin of the thermal image. It fakes the image and
  it is not AEE's physics path.
- The `#lightpoint` "second sun" as AEE's thermal path. The second sun already
  exists and stays as a display supplement, not as the model.
- A two-dimensional hot-body overlay. It is an overlay and not a model.
- A fixed sky offset. It cannot follow the weather.
- The `viewDistance` range proxy. It is not a target range.
- Copying a workshop mod's code, config, texture or array. The surveyed mods
  publish no licence, so their findings are ideas and interface shapes only.
- A Stefan-Boltzmann `eps^0.25` inversion for the band sky. It is the
  total-power inversion and it is not valid for a band.
- Inventing an MWIR transmission curve. A stated ceiling is honest and an
  invented value is not.

## Consequences and ceiling

- Both bands compute. The LWIR default is bit-identical to the pre-change
  value.
- The MWIR clear-air transmission is explicitly ceilinged.
- The StageTI texture is per-material and engine-baked. AEE ships no texture
  and cannot repaint an arbitrary object. Terrain, vegetation and rock stay
  engine-baked and are reachable only through the existing second sun.
- The native thermal renderer is compiled. AEE's moddable path for a live
  image remains the display track.
- A headless probe cannot read pixels, so the engine-native work is verified
  at the config and command level, and the pixel-level look is an
  operator-owned observation.
- The atmospheric path radiance stays isothermal, so a long slant path or a
  temperature inversion is out of the model.
- The AI IR detection model is separate from the rendered image.
