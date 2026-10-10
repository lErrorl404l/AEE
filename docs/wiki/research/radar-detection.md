# Radar detection model (issue #104)

A military radar detection model grounded in the monostatic radar range
equation, the NRL sea-clutter reflectivity model, and the ITU-R radar
horizon.  It builds on the SHF evaporation-duct finding from issue #37:
the evaporation duct is an SHF phenomenon, so radar is coherent with the
radio propagation physics already in `aee_radio`.

The model is a per-target query (one radar, one target).  It computes the
maximum detection range as the minimum of the noise, clutter and horizon
limits, with the duct applied when it traps.

## Kernels

| Kernel | Formula | Source |
|---|---|---|
| `radarRangeEquation` | `R_max = [P_t G^2 lambda^2 sigma / ((4 pi)^3 P_min)]^(1/n)` | Skolnik, Radar Handbook 3rd ed. ch. 1; MIT Lincoln Lab Lecture 4 |
| `radarNoiseFloor` | `P_min = k T_0 B F_n SNR_min` | Skolnik ch. 1 (`k = 1.38e-23`, `T_0 = 290 K`) |
| `radarHorizon` | `D_max = 4.12 (sqrt(H_a) + sqrt(H_t))` km | ITU-R P.834-2 (4/3 earth radius) |
| `radarSeaClutter` | NRL `sigma0(dB)` model | Gregers-Hansen & Mital, NRL 2012 (DTIC ADA559494) |
| `radarClutterRange` | `R_max = sigma_t / (sigma0 theta_az (c tau / 2) sec(psi) TCR_min)` | NRL 2012; Skolnik |
| `radarDuctRange` | `lambda_max = 0.085 delta^1.5`, `dM/dz = dN/dz + 0.157` | Kerr 1951; issue #37 |
| `radarDetectionRange` | `R_det = min(noise, clutter, horizon)` | issue #104 recommended model |
| `radarRcs` | class -> RCS (m^2) | UNSOURCED (see below) |

The consumer `calculateRadarDetection` reads the atmosphere and maritime
state, calls every kernel, and returns `[range m, limiting factor, detected]`.
It writes no state.

## Verified test vectors

All four vectors from the issue reproduce exactly through the sqf_lite
interpreter that executes the real SQF:

| Vector | Expected | Kernel result |
|---|---|---|
| `R_max` (1 MW, G = 1000, lambda = 0.03, sigma = 1, P_min = 1e-13) | 46.1 km | 46.148 km |
| Horizon (`H_a = 30`, `H_t = 10`) | 35.6 km | 35.61 km |
| NRL `sigma0` (VV, 10 GHz, SS3, 1 deg) | -41.2 dB | -41.189 dB |
| Clutter range (`sigma_t = 10`, `sigma0 = -40 dB`, `theta_az = 0.02`, `tau = 1e-6`, `TCR_min = 10`) | 3.3 km | 3.333 km |

## UNSOURCED values

Per the repository's UNSOURCED marker rule (data/aircraft/SCHEMA.md section 6):

- **RCS class table** (`radarRcs`).  The issue states the class ranges but
  names the wrong source.  A source check found the canonical figures in
  Skolnik, "Introduction to Radar Systems", Table 2.2 (man 1, bird 0.01,
  automobile 100, pickup truck 200, large fighter 6, large bomber 40,
  jumbo jet 100, small open boat 0.02) - NOT the "Radar Handbook" the
  issue cites.  Against that table the issue's "vehicle 5-20 m^2"
  CONFLICTS (the canonical vehicle is ~100-200 m^2); the stealth
  (0.001-0.01) and helicopter (~3) rows do not appear at all.  The values
  are the issue's range mid-points, are leads, and never fill a
  runtime-required field.  The model is gated by the
  `aee_radio_radarDetection` setting (default off) until a held source
  replaces them.
- **Duct cutoff constant** (`radarDuctRange`).  A source check found
  Kerr's cutoff is `lambda_max = c * gamma^0.5 * delta^1.5`
  (NBS J. Res. 63D(1):29, 1959, eq. 13), gradient-dependent, NOT the
  fixed `0.085 * delta^1.5` the issue states.  The issue's constant is
  used as a lead.
- **Ducted range constant** (`radarRangeEquation`, `n = 2`).  The issue's
  `R^4 -> R^2` law is implemented, but the cylindrical-spreading constant
  for the ducted case is not held, so the `(4 pi)^3` constant is retained.
  This is a simplification and is marked in the kernel header.

## Source-verification notes

- **NRL sea clutter CONFIRMED exact.**  Gregers-Hansen & Mital, NRL
  MR/5310--12-9346 (DTIC ADA559494; IEEE TAES 2012,
  DOI 10.1109/TAES.2012.6324732): the coefficients and the VV 10 GHz SS3
  1 deg value (-41.19 dB) reproduce.
- **Horizon.**  ITU-R P.834 gives the 4/3 earth radius only.  The horizon
  formula `D = sqrt(2 k R_e H)` is derived from that `k`, not quoted from
  P.834.
- **Noise floor.**  The `k`, `T_0` constants are standard.  `SNR_min` is
  taken as a parameter, so no detection-probability pairing is baked in
  (the issue's "13 dB for Pd=0.5, Pfa=1e-6" is ambiguous; Skolnik
  Fig 2.7 gives 13.1 dB for Pfa=1.11e-9).

## Honest ceilings

- **No in-engine run.**  There is no Arma server in this environment, so
  the kernels are verified through `tools/tests/sqf_lite.py` (which
  executes the real SQF), and the engine query is verified structurally.
- **Swerling fluctuation is not modelled.**  The issue flags it; a
  `Pd`-versus-range curve needs the Swerling cases, which are deferred.
- **The RCS table is a lead.**  See UNSOURCED above.

## Issue-text corrections

- The RCS table cites Skolnik, which is not held.  The values are marked
  UNSOURCED rather than presented as verified.
- The issue's Rayleigh-region note is applied: at SHF against these
  vehicle and aircraft classes the target is in the optical region, so a
  flat RCS is correct (no `lambda^-4` scaling).
