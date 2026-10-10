# Internal waves and the thermocline

This note records the ocean internal-wave and thermocline model for issue
#17. It names the formula and the source for every value, and it records
where the issue text differs from the sources. It invents no value.

## The gap

The engine models one sea surface. It has no water column, no thermocline
and no internal motion. The maritime module already publishes the sea
state, the tide and the sea-surface temperature. This model adds the two
missing pieces of the water column: the vertical temperature profile and
the internal wave that rides on the density difference it creates.

The model is the one the issue calls "minimal, honest": a two-layer
reduction, an internal tide at the M2 period, and a deterministic function
of mission time, map latitude and sea-surface temperature.

## The two-layer reduction

The continuous ocean is reduced to two layers. The upper layer is the warm
mixed layer of thickness `h1`, equal to the thermocline depth. The lower
layer is the cold deep layer of thickness `h2`, fixed at 1000 m. The
upper-layer temperature is the sea-surface temperature from
`fnc_calculateSeaSurfaceTemperature`; the lower-layer temperature is the
abyssal value.

Each layer density comes from the linear equation of state:

    rho(T, S) = rho0 * (1 - alpha * (T - T0) + beta * (S - S0))

| Constant | Value | Unit | Source |
|---|---|---|---|
| `rho0` | 1027.8 | kg/m3 | EOS-80 (Millero and Poisson 1981) at 4 degC, S = 35 |
| `alpha` | 1.7e-4 | per degC | Thermal expansion at about 10 degC, EOS-80 (Millero and Poisson 1981); the widely-cited generic figure (Stewart 2008 section 6.5) |
| `beta` | 7.6e-4 | per psu | Haline contraction at about 10 degC, EOS-80 (Millero and Poisson 1981) |
| `T0` | 4 | degC | Reference temperature (abyssal) |
| `S0` | 35 | psu | Reference salinity (standard seawater) |

Source: Gill (1982) *Atmosphere-Ocean Dynamics*, Academic Press, section
3.7, for the linear equation of state. The coefficients are the UNESCO
EOS-80 values (Millero and Poisson 1981, *Deep-Sea Research* 28:625;
UNESCO 1983, *Algorithms for Computation of Fundamental Properties of
Seawater*).

The linear form is a stated approximation. The true thermal expansion
coefficient is temperature-dependent: EOS-80 at S = 35 gives 1.0e-4 per
degC at 4 degC, 1.7e-4 at 10 degC, and 2.6e-4 at 20 degC. The single value
1.7e-4 is the mid-range figure at about 10 degC. The model uses the
density DIFFERENCE, which the linear form captures well enough for the
two-layer speed.

## The internal-wave phase speed

A density difference between two layers supports a wave on the interface.
For a long wave the phase speed is:

    g' = g * (rho2 - rho1) / rho2
    c  = sqrt( g' * h1 * h2 / (h1 + h2) )

`g'` is the reduced gravity. Because the density difference is small
(`d(rho)/rho` about 0.001 to 0.003) the reduced gravity is two to three
orders of magnitude below `g`, and the internal wave is far slower than a
surface wave.

The reduced gravity above uses the Boussinesq form with the reference
density taken as the lower layer (`/rho2`). The exact symmetric two-layer
form is `g' = g * (rho2 - rho1) / (rho2 + rho1)` (Phillips 1977, *The
Dynamics of the Upper Ocean*, page 37). The two differ by about 0.1
percent for seawater, because `d(rho)/rho` is about 2e-3. The Boussinesq
form is used here and the choice is stated.

Source: Gill (1982) *Atmosphere-Ocean Dynamics*, section 6.2, for the
two-layer phase speed and the reduced gravity. Also Turner (1973)
*Buoyancy Effects in Fluids*, Cambridge University Press, section 2.1,
Phillips (1977) page 37, and WHOI 12.800, chapter 11, "Internal Waves".

Worked example (issue #17): `g' = 0.02 m/s2`, `h1 = 50 m`, `h2 = 1000 m`
gives `c = sqrt(0.02 * 50 * 1000 / 1050) = 0.976 m/s`. The issue states
0.97 m/s. Confirmed.

The model's own numbers at mid-latitude: a mixed layer at 15 degC over a
deep layer at 4 degC, S = 35, gives `g' = 0.0267 m/s2` and `c = 1.13 m/s`,
inside the observed 0.5 to 1.5 m/s band.

## The internal tide

At the tidal frequency the thermocline rises and falls as a long internal
wave. The interface displacement is a sine of the tidal phase:

    eta(t) = A * sin(2*pi*t/T)

`A` is the displacement amplitude (operator setting, default 20 m). `T` is
the M2 period, 12.4206 h (44714 s). The M2 period is the principal lunar
semidiurnal constituent, from the Admiralty and NOAA harmonic constituent
tables.

The horizontal velocity follows from continuity. For a long two-layer
internal wave the velocity is uniform within each layer:

    u1 =  c * eta / h1     upper layer
    u2 = -c * eta / h2     lower layer

so the current is in phase with the displacement and is largest in the
thinner layer.

Source: Gill (1982) *Atmosphere-Ocean Dynamics*, section 6.2, for the
continuity relation and the layer velocities.

Correction: the issue gives the current as approximately
`zeta * sqrt(g'/h_eff)`. That is an approximation. The exact two-layer
result, `u1 = c * eta / h1`, is used instead.

## The M2 critical latitude

An internal tide exists only where the tidal frequency exceeds the
inertial frequency:

    f = 2 * Omega * sin(phi),   Omega = 7.2921e-5 rad/s

For M2 (angular frequency `omega = 2*pi/44714 = 1.405e-4 rad/s`) the
critical latitude is `sin(phi) = omega / (2*Omega) = 0.963`, so
`phi = 74.5 deg`. Poleward of 74.5 deg the M2 internal tide is
evanescent. The model reports the internal tide inactive there and sets
the displacement and the currents to zero.

Source: the inertial frequency is standard (Stewart 2008, section 6.2).
The M2 critical latitude follows from it. The evanescence of the internal
tide poleward of the critical latitude is the standard result (Simmons
2008, *Journal of Physical Oceanography* 38:1757; Garrett and Kunze 2007,
*Annual Review of Fluid Mechanics* 39:57).

The inertial period `T_i = 2*pi/f` is published as a bound on the
internal-wave band.

## The thermocline temperature profile

The temperature falls from the mixed-layer value to the deep value across
the thermocline:

    T(z) = T_deep + (T_surf - T_deep) * (1 - tanh((z - z_tc) / w)) / 2

| Parameter | Default | Unit | Source |
|---|---|---|---|
| `T_deep` | 4 | degC | Deep-water temperature. Stewart (2008) chapter 13 gives water below 1 km a potential temperature below 4 degC, so 4 degC is the warm end; the abyssal mean is about 2 to 3 degC |
| `z_tc` | 50 | m | Seasonal thermocline depth. Modelling range, consistent with the Stewart (2008) section 6.4 mixed layer of 10 to 200 m |
| `w` | 30 | m | Thermocline half-width. Modelling range, tens of metres |

The tanh form is a modelling choice. Issue #17 prescribes it. It is the
standard analytical representation of a monotonic thermocline, and it has
no single published constant. The depth and width ranges are a modelling
range consistent with the observed seasonal thermocline (Stewart 2008,
section 6.4). For reference, the published Munk (1966) abyssal profile is
exponential, not hyperbolic tangent (Stewart 2008, section 8.5).

SQF has no `tanh` command, so the kernel builds it from `exp`:
`tanh(x) = 1 - 2 / (exp(2x) + 1)`. This is the exact identity.

## Published state

`fnc_updateInternalWaves` runs once per second and publishes:

| Variable | Meaning |
|---|---|
| `aee_maritime_thermoclineDepth_m` | Thermocline centre depth (m) |
| `aee_maritime_thermoclineWidth_m` | Thermocline half-width (m) |
| `aee_maritime_mixedLayerTempC` | Mixed-layer temperature (degC) |
| `aee_maritime_deepTempC` | Deep-water temperature (degC) |
| `aee_maritime_reducedGravity_ms2` | Reduced gravity g' (m/s2) |
| `aee_maritime_internalWaveSpeed_ms` | Two-layer phase speed c (m/s) |
| `aee_maritime_internalTidePeriod_h` | M2 period (h) |
| `aee_maritime_internalWaveAmplitude_m` | Interface displacement eta (m) |
| `aee_maritime_internalCurrentUpper_ms` | Upper-layer current u1 (m/s) |
| `aee_maritime_internalCurrentLower_ms` | Lower-layer current u2 (m/s) |
| `aee_maritime_inertialPeriod_h` | Inertial period (h) |
| `aee_maritime_internalTideActive` | Boolean, M2 above the inertial frequency |
| `aee_maritime_thermoclineProfile` | `[[depth_m, tempC], ...]` for the sound-speed model |

The profile is the input the future underwater acoustics model (#113)
needs: it applies the Mackenzie (1981) sound-speed formula to the
temperature at each depth. This model does not compute sound speed.

## Out of scope

- Nonlinear internal solitons. The South China Sea extreme (about 170 m
  amplitude, 2.9 m/s phase speed, half-width about 3 km) is a nonlinear
  Korteweg-de Vries phenomenon, too heavy for the tick. The model is the
  linear internal tide. Source: Klymak et al. (2006), *Geophysical
  Research Letters* 33, L12605.
- The continuous (non-two-layer) mode structure. A full modal
  decomposition needs the full density profile and a numerical solver.
- Sound speed. That belongs to issue #113.

## Sources

- Gill, A. E. (1982). *Atmosphere-Ocean Dynamics*. Academic Press.
  Sections 3.7 and 6.2.
- Turner, J. S. (1973). *Buoyancy Effects in Fluids*. Cambridge University
  Press. Section 2.1.
- Phillips, O. M. (1977). *The Dynamics of the Upper Ocean*. Cambridge
  University Press. Page 37 (the symmetric two-layer reduced gravity and
  the deep-water dispersion).
- Stewart, R. H. (2008). *Introduction to Physical Oceanography*. Sections
  6.2, 6.4 and 6.5, and chapter 13 (the deep-water temperature).
- Millero, F. J., and Poisson, A. (1981). A new equation of state for
  seawater. *Deep-Sea Research* 28:625. UNESCO (1983). *Algorithms for
  Computation of Fundamental Properties of Seawater*. (EOS-80.)
- WHOI 12.800. Chapter 11, "Internal Waves".
- Simmons, H. L. (2008). Spectral modification and geographic distribution
  of the semi-diurnal and diurnal tides. *Journal of Physical Oceanography*
  38:1757. Garrett, C., and Kunze, E. (2007). Internal tide generation in
  the deep ocean. *Annual Review of Fluid Mechanics* 39:57.
- Klymak, J. M., et al. (2006). Prototypical solitons in the South China
  Sea. *Geophysical Research Letters* 33, L12605.
- NOAA CO-OPS harmonic constituents (M2 speed 28.984104 deg/h, period
  12.4206 h). IERS for the Earth rotation rate 7.2921150e-5 rad/s.
