# Underwater light attenuation and bioluminescence (issue #14)

The maritime module models the light field under the water surface.  The
model is the minimal honest set the issue names.  Every coefficient comes
from a published source.  The kernel set lives in
`addons/maritime/functions/`.

## Engine ceiling

Arma 3 renders its own underwater tint.  The mod cannot replace that
render.  The driver `updateUnderwaterLight` publishes the physical state to
`missionNamespace` once per second so a consumer (NVG, view distance, HUD)
can use it.  The driver does not fight the engine render.  This is the
honest scope: the physics is real and published, the render stays the
engine's.

## Beer-Lambert attenuation

Light decays with depth by the Beer-Lambert law:

    I(z) = I0 * exp(-Kd * z)

Kd is the diffuse attenuation coefficient (m^-1).  The 1 percent light
depth follows from the inverse:

    z_1pct = ln(100) / Kd = 4.605 / Kd

The model uses Kd, never the beam attenuation c = a + b.  Kd is always
smaller than c.  Kd is correct for ambient visibility and colour.  The beam
attenuation c is correct only for a point light or a discrete object.  The
two are not modelled together.

Kernel: `calculateUnderwaterLight`, `calculateLightDepth`.

## Jerlov water types

The Jerlov classification sets the minimum Kd, at the transparency peak,
and the peak wavelength (Jerlov 1976, Marine Optics).  The kernel uses the
table midpoint:

| Type | Kd (m^-1) | Peak (nm) |
|---|---|---|
| I | 0.035 | 475 |
| IA | 0.045 | 475 |
| IB | 0.055 | 475 |
| II | 0.085 | 475 |
| III | 0.15 | 500 |
| 1 | 0.17 | 500 |
| 3 | 0.275 | 525 |
| 5 | 0.425 | 550 |
| 7 | 0.625 | 560 |
| 9 | 0.90 | 575 |

The peak shifts 475 to 575 nm as dissolved matter rises.

## Pure-water absorption

Pope and Fry (1997), Applied Optics 36:8710.  The values are read from the
omlc.org digitisation of that paper.  The minimum is 0.0044 m^-1 at 418 nm.

| lambda (nm) | a_w (m^-1) |
|---|---|
| 418 | 0.0044 |
| 475 | 0.0114 |
| 530 | 0.0434 |
| 600 | 0.222 |
| 660 | 0.410 |
| 700 | 0.650 |

Kernel: `pureWaterAbsorption`.  The value between anchors is linearly
interpolated.

## Per-band derivation

The three bands are red 660 nm, green 530 nm, blue 475 nm.  Kd splits into
pure-water absorption and the dissolved plus particulate term:

    Kd(lambda) = a_w(lambda) + a_oth(lambda)

The term a_oth is dominated by gelbstoff.  Its absorption falls
exponentially with wavelength at the slope S:

    a_oth(lambda) = a_oth(lambda_peak) * exp(-S * (lambda - lambda_peak))

S = 0.014 nm^-1 (Bricaud, Morel and Prieur 1981, Limnology and Oceanography
26:43, and Twardowski and others 2004, Marine Chemistry 89:69).  The value
at the peak follows from the Jerlov table and the pure-water absorption:

    a_oth(lambda_peak) = Kd_min - a_w(lambda_peak)

Kernel: `waterTypeKd`.  The stated approximation is one dissolved-matter
exponential across the three bands.  It reproduces the measured behaviour:
clear water keeps blue longest, turbid water loses blue first, and the
transparency peak shifts red as dissolved matter rises.

## Secchi anchor

The Secchi disk measures clarity.  The diffuse attenuation follows from the
Secchi depth Zsd:

    clear water:  Kd = 1.7 / Zsd   (Poole and Atkins 1929)
    turbid water: Kd = 1.44 / Zsd  (Holmes 1970)

Typical Secchi depths: open ocean 30 to 50 m, coastal 5 to 20 m, lake 1 to
10 m, river 0.1 to 2 m.  Kernel: `calculateSecchiKd`.

## Snell window

From under the water the sky is compressed into a cone.  The cone edge is
the critical angle of total internal reflection:

    sin(theta_c) = n_air / n_water = 1 / n_water

The refractive index of seawater is 1.34 to 1.35 at visible wavelengths
(Austin and Halikas 1976, SIO Reference 76-1).  Pure water is 1.333.  The
kernel default is 1.333, which matches the issue value:

    sin(theta_c) = 0.750,  theta_c = 48.6 degrees

The full cone is 97.2 degrees.  The angle does not depend on depth.  Kernel:
`calculateSnellWindow`.

## Bioluminescence

Many dinoflagellates flash blue-green light when the water is disturbed.
The emission peaks at 472 nm for Pyrocystis noctiluca (Widder, Case and
others 1983, Biological Bulletin 165:791).  The per-cell rate is 1e9 to
1e11 photons per second, about 5e10 on average (Bachelder and Swift 1989).

The flash is gated on three conditions that hold together:

1. Darkness.  Ambient below 0.01 lux.  Light suppresses the flash.
2. Clear water.  Kd below 0.2 m^-1 (Jerlov III or better).  Turbid water
   hides the 475 nm emission.
3. Disturbance.  A positive mechanical disturbance.

The flash envelope is a double exponential:

    f(t) = exp(-t / tau_decay) * (1 - exp(-t / tau_rise))

with tau_rise = 0.077 s and tau_decay = 0.5 s.  The peak is at about
0.17 s and the total lasts about 0.5 to 0.6 s.  Kernel:
`calculateBioluminescence`.

## Corrections to the issue

Two values in the issue text were corrected against the primary source.

1. Pure-water absorption at 475 nm.  The issue lists 0.0145 m^-1.  That
   value belongs near 490 nm.  The digitisation gives 0.0114 m^-1 at
   475 nm.  The issue's 0.401 m^-1 at 660 nm is 0.410 m^-1 in the source.
2. Snell window index.  The issue's 48.6 degrees matches pure water at
   n = 1.333.  Seawater at n = 1.34 gives 48.3 degrees.  The kernel keeps
   1.333 as the default and accepts an override.

## Sources

- Jerlov (1976), Marine Optics, Elsevier.  Water types and Kd.
- Solonenko and Mobley (2015), Applied Optics 54:5392.  Jerlov IOPs.
- Pope and Fry (1997), Applied Optics 36:8710.  Pure-water absorption.
- omlc.org/spectra/water/abs.  Digitisation of Pope and Fry.
- Bricaud, Morel and Prieur (1981), Limnology and Oceanography 26:43.
  Gelbstoff spectral slope.
- Twardowski and others (2004), Marine Chemistry 89:69.  CDOM slope range.
- Austin and Halikas (1976), SIO Reference 76-1.  Seawater refractive
  index.
- Poole and Atkins (1929).  Secchi to Kd, clear water.
- Holmes (1970).  Secchi to Kd, turbid water.
- Widder, Case and others (1983), Biological Bulletin 165:791.
  Dinoflagellate emission peak.
- Bachelder and Swift (1989).  Dinoflagellate photon rate.
- Latz and others (1994), Limnology and Oceanography 39:1424.  Flash
  kinetics.  Cited in the issue.  Not independently verified, the paper is
  behind a paywall.
