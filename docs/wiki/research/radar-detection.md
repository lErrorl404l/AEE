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
| `radarDuctRange` | `lambda_max = 8.32e-4 delta^1.5` m (Kerr eq. 18 converted), `dM/dz = dN/dz + 0.157` | Kerr 1951 sec. 1-5 eq. (18); NPS NWDC EM course module 4.2 |
| `radarDetectionRange` | `R_det = min(noise, clutter, horizon)` | issue #104 recommended model |
| `radarRcs` | class -> RCS (m^2) | Skolnik, Introduction to Radar Systems 2nd ed. Table 2.2; NAWCWD TP 8347 4-11 (see below) |

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

## Sourced values

- **RCS class table** (`radarRcs`).  The sourced rows are the published
  figures from Skolnik, "Introduction to Radar Systems", 2nd ed.,
  McGraw-Hill, 1981, Table 2.2, p. 44: large fighter 6 m^2, large bomber
  40 m^2, man 1 m^2, automobile 100 m^2, small open boat 0.02 m^2.  The
  issue named Skolnik's "Radar Handbook", which does not carry this table;
  the class range mid-points it gave (vehicle 5-20 m^2) conflict with the
  published automobile 100 m^2 and were replaced.
- **Duct cutoff** (`radarDuctRange`).  Kerr, "Propagation of Short Radio
  Waves", MIT Radiation Laboratory Series vol. 13, 1951, section 1-5 eq.
  (18): `lambda_max = 0.014 d^1.5` cm with d in feet, i.e.
  `8.32e-4 d^1.5` m with d in metres (the commonly quoted
  `0.085 delta^1.5` is Kerr's constant in centimetres).  Corroborated by
  the Naval Postgraduate School NWDC Electromagnetic Course, module 4.2
  (`f_M = 360 delta^-1.5` GHz).  The gradient-dependent form is Bean, NBS
  J. Res. D 63(1):29-34, 1959, eq. (13).  The earlier use of a bare 0.085
  as a metre-valued constant was a unit error of about 100x.

## Game tunables

- **RCS rows with no published scalar** (`radarRcs`): stealth 0.00316
  (the issue's range 0.001-0.01), helicopter 3 (no single representative
  figure; helicopter RCS is dominated by dynamic rotor scattering), and
  ship 3000 (NAWCWD TP 8347 section 4-11 publishes only a range, "ships
  3,000 to 1,000,000 sq m").  Each row is marked a game tunable in the
  kernel.
- **Ducted range constant** (`radarRangeEquation`, `n = 2`).  The issue's
  `R^4 -> R^2` law is implemented, but the cylindrical-spreading constant
  for the ducted case is not held, so the `(4 pi)^3` constant is retained.
  This is a documented simplification and is marked in the kernel header.

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
- **The RCS rows without a published scalar are game tunables.**  See
  Game tunables above.

## Issue-text corrections

- The RCS table cited Skolnik's "Radar Handbook", which does not carry the
  table.  The sourced figures are from "Introduction to Radar Systems",
  2nd ed., Table 2.2, p. 44.
- The issue's Rayleigh-region note is applied: at SHF against these
  vehicle and aircraft classes the target is in the optical region, so a
  flat RCS is correct (no `lambda^-4` scaling).
