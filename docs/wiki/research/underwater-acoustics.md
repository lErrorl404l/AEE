# Underwater acoustics and sonar: verified research boundary (issue #113)

This page records the formulas, the sources, and the honest engine scope of
the underwater acoustics model. Every value traces to a named primary source
or is marked UNSOURCED. The model is a set of pure kernels plus a driver that
publishes the environmental state; it does not add a second model of the
atmospheric sound propagation in the ambience addon (issue #80), which is
air (c about 343 m/s) and a different domain.

## 1. Sound speed in seawater (Mackenzie 1981)

```
c = 1448.96 + 4.591 T - 5.304e-2 T^2 + 2.374e-4 T^3
    + 1.340 (S - 35) + 1.630e-2 D + 1.675e-7 D^2
    - 1.025e-2 T (S - 35) - 7.139e-13 T D^3
```

Source: Mackenzie, K. V. (1981), "Nine-term equation for sound speed in the
oceans", JASA 70(3):807-812, DOI 10.1121/1.386920. T in degC, S in psu, D in
m, c in m/s. The nine-term form is the full published equation; the two cross
terms vanish at S=35, D=0, so a seven-term truncation agrees on the axis.

Worked example: T=10, S=35, D=0 gives 1489.8 m/s. The issue records the same
correction; the common "1481 m/s" figure is fresh water at 20 C.

UNSOURCED: the validity ranges (commonly reproduced as 0-30 C, 30-40 psu,
0-8000 m). The primary is paywalled and was not read this session.

## 2. Seawater absorption (Francois-Garrison 1982)

```
alpha = A1 P1 f1 f^2 / (f1^2 + f^2)
      + A2 P2 f2 f^2 / (f2^2 + f^2)
      + A3 P3 f^2                 dB/km
```

Source: Francois, R. E. and Garrison, G. R. (1982), "Sound absorption based on
ocean measurements: Part II", JASA 72(6):1879-1890, DOI 10.1121/1.388673. The
kernel uses the paper's own sound speed, `c = 1412 + 3.21 T + 1.19 S +
0.0167 D`, not the Mackenzie value: the coefficients were fitted against this
linear form.

| Quantity | Formula |
|---|---|
| Boric acid amplitude | `A1 = 8.86 / c * 10^(0.78 pH - 5)` |
| Boric acid relaxation | `f1 = 2.8 sqrt(S/35) * 10^(4 - 1245/(T+273))` kHz |
| MgSO4 amplitude | `A2 = 21.44 S / c * (1 + 0.025 T)` |
| MgSO4 relaxation | `f2 = 8.17 * 10^(8 - 1990/(T+273)) / (1 + 0.0018 (S-35))` kHz |
| Pure water (T<=20 C) | `A3 = 4.937e-4 - 2.59e-5 T + 9.11e-7 T^2 - 1.5e-8 T^3` |
| Pure water (T>20 C) | `A3 = 3.964e-4 - 1.146e-5 T + 1.45e-7 T^2 - 6.5e-10 T^3` |
| MgSO4 pressure | `P2 = 1 - 1.37e-4 D + 6.2e-9 D^2` |
| Pure water pressure | `P3 = 1 - 3.83e-5 D + 4.9e-10 D^2` |

Computed anchors (T=10 C, S=35 psu, D=0 m, pH=8): 0.0012 dB/km at 100 Hz,
0.070 dB/km at 1 kHz, 0.99 dB/km at 10 kHz, 34 dB/km at 100 kHz.

CORRECTED ISSUE VECTORS. The issue states "0.01-0.1 dB/km at 100 Hz" and
"about 50 dB/km at 100 kHz". The equation gives 0.0012 and 34 dB/km. The
issue's 10 kHz band (0.1-1) is correct. The kernel and the tests use the
equation values.

UNSOURCED: the validity ranges (commonly T -4..30 C, S 30..35 ppt, D
0..1000 m, pH 7.5..8.5, f 200 Hz..1 MHz). The primary is paywalled.

## 3. Transmission loss and the sonar equation (Urick)

```
spherical:   TL = 20 log10(r) + alpha r
cylindrical: TL = 10 log10(r) + alpha r
passive:     SE = SL - TL - NL + DI
active:      SE = SL - 2 TL + TS - NL + DI
```

Detection occurs when SE >= DT. Source: Urick, "Principles of Underwater
Sound", 3rd ed., McGraw-Hill 1983, ISBN 0-07-066087-5, ch. 5-6. Corroborated
by the US Naval Academy ES310 sonar-propagation notes. The detection range
inverts TL(r) = EL by bisection, with `EL_passive = SL - NL + DI - DT` and
`EL_active = (SL + TS - NL + DI - DT) / 2`.

UNSOURCED: the example numbers the issue gives (source levels 220-235 dB,
submarine target strength 10-25 dB, ship 30-50 dB, passive range 10-100 km,
active 1-20 km). These are standard Urick values but were not re-read from the
primary this session. The detection-range kernel defaults are set to produce a
submarine passive range near 95 km, inside the issue's stated band.

## 4. Ambient noise (Wenz 1962)

Source: Wenz, G. M. (1962), "Acoustic Ambient Noise in the Ocean: Spectra and
Sources", JASA 34(12):1936-1956, DOI 10.1121/1.1909155.

Wenz published the spectrum as GRAPHICAL curves, not a closed form. There is
no citable analytic parameterisation. The model is therefore a stated
approximation:

- Sea-state component at 1 kHz: `L = 40 + 5 SS` dB re 1 uPa^2/Hz (SS 0..6),
  anchored to the issue's readings (SS0 40, SS3 55-60, SS6 70).
- Frequency shape and the shipping band below 500 Hz are UNSOURCED stated
  approximations.
- Shallow water is louder (a fixed UNSOURCED bonus).

The reference convention is dB re 1 uPa^2/Hz. The driver clamps the mod's
Beaufort number to the Wenz 0..6 range; the Beaufort-to-sea-state mapping is
UNSOURCED.

## 5. Sound channel, ray bending and the shadow zone

The ray invariant across a horizontally stratified medium is `cos(theta) / c =
constant`, so `cos(theta2) = (c2/c1) cos(theta1)`: a ray bends toward the
slower sound speed. When `(c2/c1) cos(theta1) >= 1` the boundary is a turning
point. Source: Urick ch. 6.

The SOFAR channel axis is the depth of least sound speed; the model finds it
from the profile (fnc_calculateSoundChannel). The channel traps sound between
the surface and the axis so a signal can travel thousands of kilometres
(described independently by Ewing and Worzel and by Brekhovskikh).

The direct-path shadow zone is the band below the axis, where rays from a
shallow source have all refracted downward and away. Source: the mechanism is
confirmed by the ES310 notes; Urick gives the convergence-zone geometry.

CEILING. The quantitative "best depth" rule for the shadow zone is not a
closed form and is NOT reproduced. The range-dependent boundary (the first
convergence zone, which refills the shadow beyond 20-30 nautical miles) is NOT
modelled. The kernel reports the direct-path band below the axis, which is the
honest answer within the engine scope.

UNSOURCED: the exact SOFAR axis depth (commonly about 1000 m at mid-latitudes)
and the exact "20 Hz Bermuda-to-Bahamas" experiment details. The axis follows
the local profile in the model, not a fixed constant.

## 6. What the model does and does not do

Published state (read by the sonar query and by scenarios):
`aee_maritime_soundSpeedSurface`, `soundChannelAxisDepth_m`,
`soundChannelAxisSpeed`, `shadowZoneTop_m`, `shadowZoneBottom_m`,
`absorptionDbPerKm`, `ambientNoiseDb`.

The model does not compute a full range-dependent ray trace, a convergence
zone, or a bottom-bounce path. It does not add engine sound: the driver
publishes physics state for scenarios, divers and the sonar equation.
