# Atmospheric optical phenomena

## Purpose

This note records the physics behind AEE's ice-crystal halo and green-flash
models, the formulas, and the sources. The design decision on scope is in the
issue #12 record and in the model headers.

## What AEE already modelled

Three of the phenomena in issue #12 were already present before this work, and
were not rebuilt:

- **Mirage.** `aee_atmos_fnc_calculateRefraction` derives the mirage type
  (Inferior, Superior, Looming, Towering, None) from the ITU-R P.453
  refractivity gradient. The ducting branch (`dN/dh <= -157 N/km`) is the same
  condition the issue names as full mirage trapping. The heat-haze visual
  effect is `aee_optics_fnc_calculateMirageIntensity` with
  `aee_optics_fnc_applyMirageFX`.
- **Rainbow.** `aee_atmos_fnc_updateRainbow` drives the engine rainbow from the
  sun elevation, rain and the anti-solar view direction.
- **Solar glare.** `aee_optics_fnc_calculateSolarGlare` and
  `aee_optics_fnc_applySolarGlareFX`.

This work adds the two that were missing: the halo (with parhelia) and the
green flash.

## Halo: hexagonal ice prisms

The 22-degree and 46-degree halos are the minimum-deviation rays through the
60-degree and 90-degree prism faces of hexagonal ice crystals. The angular
radius is the prism minimum deviation:

    D_min = 2 * asin( n * sin(A/2) ) - A

- `A = 60 deg` gives the 22-degree halo.
- `A = 90 deg` gives the 46-degree halo.

The hexagonal ice refractive index in the visible band is 1.306 (red, 656 nm)
and 1.317 (blue, 486 nm) (Warren and Brandt 2008, JGR 113 D14220,
doi:10.1029/2007JD009216). The red index bounds the sharp inner edge and the
blue index the diffuse outer edge, so the ring has a small chromatic width.
With those indices the model gives a 21.5-22.4 deg inner/outer pair for the
22-degree halo and a 44.9-47.3 deg pair for the 46-degree halo.

Parhelia (sundogs) sit on the 22-degree halo circle at the sun's elevation.
Their azimuth offset from the sun follows from the halo being a circle of
angular radius 22 deg about the sun:

    cos(delta_az) = ( cos(22 deg) - sin^2(elev) ) / cos^2(elev)

They spread outward as the sun rises and fade near 61 deg solar elevation
(Tape 1994, Atmospheric Halos, Antarctic Research Series 64; Cowley,
atoptics.co.uk).

`aee_atmos_fnc_calculateHalo` computes all of this and publishes
`aee_atmos_haloIntensity`, `aee_atmos_haloActive`, the four ring radii and the
parhelion offset.

## Green flash: refraction dispersion

The green flash is the last green sliver of the sun's upper limb as it crosses
the horizon. It is not a separate light source: it is the dispersion of
atmospheric refraction magnified by a mirage (Young, SDSU). Refraction lifts
the whole disc, and dispersion lifts the green image slightly more than the
red, so the green rim is the last part to set. The red image has already set,
and haze removes the violet and blue, so only green remains.

- Horizon refraction `R(h)` is 0.53-0.57 deg (Saemundsson and Bennett).
- The fractional dispersion of air, `d(n-1)/(n-1)`, is about 0.025 (red to
  green).
- The angular red-green separation at the horizon is `deltaR = R(h) * 0.025`.
- The sun's limb crosses the horizon at 0.25 deg/min, so the rim shows for
  `deltaR / (0.25/60)` seconds, about 1-2 s.

`aee_optics_fnc_calculateGreenFlash` computes the intensity and the rim
duration, and publishes `aee_optics_greenFlashIntensity`,
`aee_optics_greenFlashActive` and `aee_optics_greenFlashDurationS`. It is gated
on the sun's upper limb within about 0.5 deg of the horizon, a mirage (a
refractivity gradient at or below -100 N/km), and a clean horizon (low haze and
low overcast).

## Engine surface and scope

The engine has no command for a halo ring or a sun-limb colour. The phenomena
are modelled as physics kernels that publish state, in the same shape as the
existing mirage, seeing and glare kernels. A renderer that draws the ring or
tints the limb is a separate, later decision: it needs an art surface (a sprite)
or an astronomy-layer draw path, and neither is in this issue's scope. The
model publishes the ring radii and the parhelion offset so a renderer can
consume them without re-deriving the geometry.

## Sources

- Tape, W. (1994) Atmospheric Halos, Antarctic Research Series 64.
- Minnaert, M. (1993) Light and Color in the Outdoors.
- Warren, S. G. and Brandt, R. E. (2008) Optical constants of ice from the
  ultraviolet to the microwave, JGR 113, D14220, doi:10.1029/2007JD009216.
- Cowley, L. atoptics.co.uk (parhelia and halo geometry).
- Young, A. T. (SDSU) "Green flashes" and "An introduction to mirages".
- Saemundsson (1986) and Bennett (1982) atmospheric refraction formulas.
- Issue #12 (2026-09-16) green-flash model and constants.
