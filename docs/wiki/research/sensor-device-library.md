# Night Vision / Thermal / Optic Device Library Research (issue #215)

Research basis for the sensor device library.  All values from
manufacturer datasheets (L3Harris, Elbit, Thales, Safran, FLIR,
Trijicon, Aimpoint, ELCAN, NPZ), army manuals and NSN records.
Real-world only, never invented.

## NVG devices (image intensifier)

Key corrections that matter for the tube model:
- FOM = SNR x resolution (lp/mm), NOT resolution x gain.
- GPNVG-18 is <0.8 kg goggle (not 2.5 kg; that is the full mounted
  system).
- Ops-Core AMP is hearing protection, not an NVG.
- 1PN140/141/144 are thermal sights (Shakhin), not II tubes.

| Name | Country | Gen | Photocathode | Resolution | FOV | Weight_kg | Source |
|---|---|---|---|---|---|---|---|
| AN/PVS-5 | US | Gen 2 | S-25 (MX-9916) | 28 | 40 unverified | 0.85 | nv-intl.com (distributor) |
| AN/PVS-7D | US | Gen 3 | GaAs (F5001) | 64 typ | 40 unverified | 0.68 | Exelis, but the sheet found is for the PVS-7 not the 7D |
| AN/PVS-14 | US | Gen 3 | GaAs (MX-11769) | 64-72 | 40 | 0.355 max | Elbit; MIL-PRF-49324D |
| AN/PVS-15 | US | Gen 3 | GaAs (thin-film) | 45-64 | 40 unverified | 0.726 | nitevis.com (distributor) |
| AN/PVS-31A BNVD | US | Gen 3 | GaAs WP | 64-72 (FOM 1600-2376) | 40 | <0.45 | L3Harris |
| BNVD-FUSED (F-BINO) | US | Gen 3 + LWIR | GaAs WP (PVS-31A tubes) | 64-72 | 40 I2 / 34 diag thermal | n/s | TNVC (distributor, no manufacturer corroboration) |
| AN/PVS-31C | US | Gen 3+ unfilmed | GaAs P-45 | 72 min (FOM 2376) | 40 unverified | <0.45 | L3Harris (SNR 33, which is not a field-of-view spec) |
| GPNVG-18 | US | Gen 3+ | 4x MX-10160 | 64-72 | 97H x 40V | 0.77-0.80 | L3Harris |
| ENVG-B (AN/PSQ-42) | US | Gen 3 + LWIR | GaAs WP | 72 (FOM 2304) | 40 | <1.133 w/batt | L3Harris F6025 |
| ENVG-III | US | Gen 3 + thermal | GaAs | n/s | 40 | n/s | army.mil |
| AN/PSQ-20 | US | Gen 3 + microbol | GaAs | 64 min | 40 I2 / 28-30 IR | <0.907 | PEO Soldier |
| Pilos | UK | Gen 2/2+/3/4G | S-25/GaAs | n/s | 40 | <0.28 | Qioptiq |
| LUCIE | FR | Gen 2+ | S-25 (XD4/XR5) | n/s | 51 | 0.435 | Thales |
| Mikron | DE/BE | Gen 2+/3 | 16mm tubes | n/s | >40 | <0.47 | OCCAR |
| 1PN58 (NSPUM) | RU | Gen 1 | S-20 (3EP32M) | 30 | 5H x 4V | 2.0 | ru.wiki |
| 1PN63 (Quaker) | RU | Gen 1 | S-20 | n/s | 40 | 1.0 | ru.wiki |
| 1PN93-1..4 | RU | Gen 2+/3 | S-25/GaAs | n/s | 6-10 | 1.0-1.5 | ru.wiki |
| 1PN138 | RU | Gen 2+/3 | n/s | n/s | 40 | 0.35 | Ratnik (27.5mm f/1.2) |
| NVT-7/14 clones | CN | Gen 2+ | S-25 | 64-68 | 40 | 0.28-0.35 | NNVT tubes |

Field of view: the axis is not published.  Elbit's AN/PVS-14 spec block
reads "Field of View - 40 nominal" with "Objective Lens EFL 27 mm" and no
axis, and L3Harris reads "Flexible 40 Field-Of-View" with no axis, so no
manufacturer in this family pins the 40 to horizontal, vertical or diagonal.
The one sheet that does name an axis is the L-3 Warrior Systems AN/PVS-31A
sell sheet, which prints "40 +/- 2 deg. (horizontal & vertical)" and, on
the same sheet, "This document consists of basic marketing information that
is not defined as technical data".  A document that calls itself
non-technical is not the citation that pins the axis, and 40 on both axes
is not credible at Elbit's own 27 mm EFL, because it needs about a 27.8 mm
image circle diagonal, which is larger than a 30 mm tube's usable area.
40 diagonal at 27 mm EFL needs about 19.7 mm, which fits.  That is a
consistency check on published inputs, not a source figure.  No horizontal
or vertical figure is published separately anywhere in the family, so the
aspect cannot be computed from real numbers.  Rows marked "unverified"
carry a 40 for which no primary source was obtained; the row is kept
because an absent row hides the gap and a marked row records it.

- AN/PVS-5: the figure reaches AEE through a distributor listing, so no
  manufacturer sheet was read for it.
- AN/PVS-7D: the datasheet found is for the PVS-7, not the PVS-7D, and it
  is a distributor sheet.  Exelis is inside Elbit and exelisinc.com does
  not resolve, so the original sheet could not be obtained.
- AN/PVS-15: the figure reaches AEE through a distributor listing, so no
  manufacturer sheet was read for it.
- AN/PVS-31C: the L3Harris material read gives the SNR 33 tube data, which
  is not a field-of-view specification, so the 40 is not sourced.

Standards coverage is not established.  MIL-PRF-49324D and STANAG 4347
could not be read: the QuickSearch host fails and NATO STANAGs are not
freely published.  The Elbit datasheet does cite MIL-PRF-49324D as the
PVS-14 build spec, so that specification exists and is the right place to
look, but its field-of-view clause is unread.  No claim is made here about
whether a standard covers a fused channel's relative field of view.

Fused devices: the documentation's word is OVERLAY, not a bounded window.
L3Harris names "white-hot, black-hot and outline modes"; TNVC names "I2
Only, Fused + NAV, I2 + NAV, and I2 Standby".  Both say the thermal is
overlayed onto the I2 image, and no source describes a bounded window.
The 34-diagonal thermal field against the PVS-31A's 40 makes the thermal
channel geometrically NARROWER than the intensified side, 34/40 = 0.85 of
it, which supports a bounded model on the numbers and not on the prose.  The
BNVD-FUSED row is distributor-strength: no L3Harris or Army corroboration
was found.  For the ENVG-B (AN/PSQ-42) there is NO published
thermal-channel figure at all, because L3Harris publishes one fused 40
covering both channels.  That figure is not split here, and the
BNVD-FUSED's 34 is not borrowed for it, because the two are different
device families.

Tube generation physics (for fnc_applyNVGTubeModel):

| Gen | Photocathode | Sensitivity | Gain | Resolution |
|---|---|---|---|---|
| Gen 0 | S-1 (Ag-O-Cs) | <60 uA/lm | <200 | 20-60 lp/mm |
| Gen 1 | S-20 | <160-200 uA/lm | <800 | 20-60 |
| Gen 2 | S-25 | ~240 uA/lm | 18,000-25,000 | 28-51 |
| Gen 2+ | S-25 | to 700 uA/lm | 25,000-26,000 | 47-64 |
| Gen 3 | GaAs | 900-1600 uA/lm | 30,000-50,000 | 42-72 |
| Gen 3+ filmless | GaAs | n/s | n/s | 72 min, SNR 33, FOM 2376 |

Shot noise = 1/sqrt(photonCount+1) is consistent with Poisson emission;
per-gen SNR (4.5 Gen 2, 21-33 Gen 3) gives the noise floor.  AGC and
gating are real (PVS-14 autogated, PVS-31C auto-gated, Photonis
0.2-0.4 s).

## Thermal devices

Detector physics basis: uncooled microbolometer NETD 40-60 mK (LWIR
8-14 um); cooled InSb 20-30 mK (MWIR 3-5 um); cooled MCT <25 mK.
Resolution 160x120 to 1280x1024; refresh 30 Hz (US mil), 50 Hz (Pulsar/
Chinese), 50/60 Hz (cooled).  FOV is lens-dependent - encode per lens.

| Name | Country | Detector | Resolution | NETD | Weight_kg | Source |
|---|---|---|---|---|---|---|
| AN/PAS-13E(V)1 LWTS | US | uncooled VOx | 320x240 | <50 | 0.885 | Raytheon |
| AN/PAS-13E(V)2 MWTS | US | uncooled VOx | 640x480 | <50 | 1.134 | Raytheon |
| AN/PAS-13E(V)3 HWTS | US | uncooled VOx | 640x480 | <50 | 1.497 | Raytheon |
| AN/PAS-29 COTI | US | uncooled LWIR | 320x240 | ~50 | 0.15 | Optics1/Safran |
| AN/PSQ-42 ENVG-B | US | uncooled 12um fused Gen3 | 640x480 | ~40 | 1.133 | L3Harris |
| FLIR Recon V | US | cooled MWIR | 640x480 | ~25 | ~1.6 | FLIR |
| FLIR Scout III 640 | US | uncooled VOx | 640x512 | ~50 | 0.34 | FLIR |
| Safran JIM LR | FR | cooled InSb | 384x288 | ~25 | <2.8 | Safran |
| Thales Sophie | FR | uncooled | 384x288/640x480 | ~50 | ~2.0 | Thales |
| Thales Sophie Ultima | FR | cooled MWIR | 640x512 | ~25 | <2.5 | Thales |
| Catherine-MP LW | FR/UK | cooled MCT | 1280x1024 | <25 | 7.9 | Thales |
| 1PN97 Mowgli-2M | RU | uncooled LWIR | 320x240 | ~50 | ~1.5 | Kalashnikov |
| 1PN139/140 Shakhin | RU | uncooled | 160x120-640x480 | ~50 | 1.3-2.2 | gunrf.ru |
| Pulsar Thermion XP50 | RU/BY | uncooled 17um | 640x480 | <25 | 0.9 | Pulsar |
| Pulsar Helion | RU/BY | uncooled | 384x288 | <40 | ~0.5 | Pulsar |

No public hard data (do not invent): AN/PAS-24, AN/PVS-32, CIV,
CoraLight, TIMM, most 1PN-series, IRBIS, TP-1/MTR-1/MA-1.  Model these
on the closest documented family (1PN-series on Shakhin, IRBIS on
Pulsar Helion-class).

Not thermal (exclude): M150 RCO/M320 (day optics), RAPTAR (1550 nm
LRF), AN/PVS-29/PVS-30 (Gen 3 II clip-ons, not thermal).

## Rifle optics

Optics physics: exit pupil = objective/magnification (PSO-1 24/4 =
6 mm); FOV falls as magnification rises (~24/mag deg for 4x-class);
eye relief 70-90 mm fixed scopes, unlimited red dots.  Weight by class:
red dot 0.09-0.40 kg, 1-4x 0.54-0.61, 4x 0.30-0.60, 10x 0.68,
5-25x 0.97-1.08.  Active (NVG/thermal) adds 1.5-2 kg.

| Name | Country | Type | Mag | Obj | FOV | Weight_kg | Source |
|---|---|---|---|---|---|---|---|
| ACOG TA31 | US | prism | 4x | 32 | 7.0 | 0.42 | Trijicon |
| ACOG TA11 | US | prism | 4x | 32 | 7.0 | 0.34 | Trijicon |
| M68 CCO (CompM2) | US | red dot | 1x | 30 | n/a | 0.40 | Aimpoint |
| CompM4 | US | red dot | 1x | 23 | n/a | 0.27 | Aimpoint |
| M150 RCO | US | prism | 4x | 32 | 7.0 | 0.42 | Trijicon |
| SpecterDR 1-4x | US/CA | variable | 1-4x | 30 | 24/8 | 0.60 | ELCAN |
| M145 MGO (C79) | US/CA | fixed | 3.4x | 28 | 8.5 | 0.68 | ELCAN |
| EOTech EXPS3 | US | holo | 1x | n/a | n/a | 0.32 | EOTech |
| Aimpoint T-2 | SE | micro dot | 1x | 20 | n/a | 0.09 | Aimpoint |
| SUSAT L9A1 | UK | fixed | 4x | 25.5 | 10 | 0.42 | NSN |
| Hensoldt ZF 4x | DE | fixed | 4x | 24 | 8 | 0.50 | Hensoldt |
| PSO-1 | RU | fixed | 4x | 24 | 6 | 0.60 | NPZ |
| 1P78 Kashtan | RU | fixed | 4x | 24 | 10 | ~0.50 | NPZ |
| 1P87 | RU | red dot | 1x | n/a | n/a | ~0.25 | NPZ |
| 1PN51/93/120 NVG sights | RU | NVG | 3.5x | 50 | 5 | ~2.0 | NPZ |
| Leupold Mark 4 M3 | US | fixed | 10x | 40 | 3.5 | 0.68 | Leupold |
| S&B PM II 5-25x56 | DE | variable | 5-25x | 56 | 4.5/1.5 | 0.97 | S&B |
| Nightforce ATACR 5-25x56 | US | variable | 5-25x | 56 | 4.5 | 1.08 | Nightforce |
| POSP 4-8x | BY | fixed | 4-8x | 24-42 | 6-3 | 0.60-0.80 | BelOMO |
| 1P69 Hyperon | RU | variable | 3-10x | 42 | 6 | ~0.90 | NPZ |

Reticle types: BDC (ACOG, PSO-1), mil-dot (Leupold, Nightforce), MOA
(S&B, USO), chevron (1P78), red dot (CompM4, T-2), holographic (EOTech).