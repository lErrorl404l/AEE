# Dense gas dispersion (issue #120)

The CBRN heavy-gas model. A gas heavier than air does not disperse like
the neutral Gaussian plume (#105): it slumps outward under its own weight,
collects in hollows, and holds its density until it dilutes past a
threshold. This dossier records every value and formula the kernels in
`addons/weather/functions/dispersion/` use, and the source for each.

Every value is grounded in a named source. Values with no published source
are marked UNSOURCED and are either exposed as a caller-set parameter or
carried as the absence of a figure (a zero), never invented.

## 1. Agent properties (`fnc_getGasProperties.sqf`)

The density ratio at equal temperature and pressure is the ideal-gas
result `rho_g / rho_a = M_gas / M_air`, with the dry-air molar mass
`M_air = 28.97 g/mol` (ISO 2533). Molar masses are the IUPAC/CIAAW atomic
weights.

| Agent | M (g/mol) | Ratio rho_g/rho_a | Normal bp (C) | Vapour pressure |
|---|---|---|---|---|
| Hydrogen cyanide | 27.03 | 0.933 | 25.6 | - |
| Carbon dioxide | 44.01 | 1.519 | -78.5 | - |
| Chlorine | 70.90 | 2.447 | -34.04 | 6.8 bar at 20 C |
| Phosgene | 98.91 | 3.414 | 7.6 | - |
| Sarin (GB) | 140.09 | 4.836 | 158 | - |
| CS | 188.61 | 6.511 | - (solid) | 3.4e-5 mmHg at 20 C |

The issue's "1.98 / 3.2 at 0 C" figures are absolute densities in kg/m3,
not ratios; the ratios are the ideal-gas values above.

## 2. Gravity slumping (`fnc_calculateDenseGasSlumping.sqf`)

Source: DEGADIS User's Manual (Havens & Spicer 1985, USCG-D-24-85, DTIC
ADA171524).

- Reduced density ratio: `A' = (rho - rho_a) / rho_a`; the issue's reduced
  gravity `g' = g * A'`.
- Frontal (slumping) velocity, Eq 1-1: `u_f = C_e * sqrt(g * A' * H)`,
  `C_e = 1.15`. The coefficient comes from the dense-gas slumping
  experiments (Schmidt 1911; Benjamin 1968; Fannelop et al. 1980; Huppert
  & Simpson 1980).
- Bulk release Richardson number: `Ri* = g * A' * H / u^2` (DEGADIS Vol I,
  after van Ulden 1974). The raw `Ri*` is returned.
- Frontal entrainment velocity, Eq II-12: `u_e = e * u_f`. DEGADIS's
  shipped default is `e = 0.59` (Vol III listing, "epsilon ... USED IN AIR
  ENTRAINMENT SPECIFICATION"); the report text quotes 0.60.

Test vector (issue): rho = 2 rho_a, H = 1 m gives
`u_f = 1.15 * sqrt(9.80665) = 3.60 m/s`.

UNSOURCED: the issue's regime cut points `Ri* > 30`, `1-30`, `< 1` are not
in DEGADIS and are not applied. The report gives passive as `Ri* -> 0`
(Fryer & Kaiser at `Ri* < 0.1`; Picknett at `Ri* = 7`), but no single
three-way split.

## 3. Mixture density and the dense/neutral transition
(`fnc_calculateGasMixtureDensity.sqf`)

Volume mixing gives `rho_mix = rho_a + C * (1 - rho_a / rho_g)`, so
`rho_mix / rho_a = 1 + (C / rho_a) * (1 - rho_a / rho_g)`.

DEGADIS stops the gravity-spreading calculation when the density excess
falls below `delrhomin = 0.025` (the shipped default). Inverting the
threshold gives the transition concentration
`C_trans = rho_a * delrhomin / (1 - rho_a / rho_g)`.

For chlorine at 20 C (`rho_a = 1.204 kg/m3`) the DEGADIS threshold gives
`C_trans = 0.051 kg/m3` (51 g/m3). The issue's "ratio < 1.1" rule
(UNSOURCED) gives `0.204 kg/m3`, i.e. **204 g/m3**. The issue prints this
as "204 mg/m3", a factor-1000 unit slip; the value is 204 g/m3. The
threshold is exposed as the `deltaRhoMin` argument (0.1 reproduces the
issue's 204 figure) with the DEGADIS value as the default.

## 4. Liquid-pool evaporation (`fnc_calculatePoolEvaporation.sqf`)

Source: Kawamura & Mackay 1987, Journal of Hazardous Materials
15(3):343-364 (also Environment Canada EE-59, 1985), with the
mass-transfer coefficient from Mackay & Matsugu 1973.

- Flux: `E = k * M * P(Ts) / (R * Ts)` (g/m2/h), `R = 8.314 J/mol/K`.
- Coefficient: `k = 0.029 * u^0.78 * X^-0.11 * Sc^-0.67` (m/h), with `u`
  the wind speed in m/h at 10 m, `X` the pool diameter in m.

The returned value is in kg/m2/s. Chlorine is a liquefied gas (bp
-34.04 C), so a pool holds at its boiling point where the vapour pressure
is one atmosphere; the driver selects this surface temperature when the
agent's boiling point is below ambient.

UNSOURCED: the default Schmidt number 0.7 (a modelling choice; most
vapours fall in 0.6 to 1.0), exposed as a parameter. Pool-spreading
regimes (Fay 1969; Webber 1991) were not fetched and are not implemented.

## 5. Pooling in terrain (`fnc_calculateDenseGasPooling.sqf`)

`P_cell = max(0, h_neighbour_mean - h_cell)`,
`C_eff = C_plume * (1 + k_pool * P_cell)`.

UNSOURCED. No published dense-gas model uses this form; real models use
three-dimensional CFD or terrain downwash (AERMOD), and DEGADIS is a
flat-ground box. The form and the default `k_pool = 0.5` are a modelling
choice, exposed as a parameter, and the kernel says so.

## 6. Acute toxic endpoints (`fnc_classifyToxicExposure.sqf`)

Endpoints (from `fnc_getGasProperties.sqf`) are the published values:

- Chlorine: EPA AEGL final (25 C, 24.45 L/mol) - AEGL-2 2.0 ppm, AEGL-3
  20 ppm at 60 min; NIOSH IDLH 10 ppm; NIOSH REL 0.5 ppm ceiling.
  Converted with `mg/m3 = ppm * M / 24.45` (M = 70.90).
- CS: EPA AEGL final, mg/m3 - AEGL-2 0.083 (all durations), AEGL-3 11 at
  60 min; NIOSH IDLH 2 mg/m3 (Pocket Guide 0122); ACGIH TLV ceiling
  0.4 mg/m3.

The classifier orders by severity (`aegl-3 > idlh > aegl-2 > tlv`) and
skips an endpoint passed as 0, so an agent with no acute data classifies
as "none" rather than against an invented figure.

UNSOURCED: the issue's "0.004 mg/m3 eye-irritation TC50", the CS particle
size (1-10 um, MMAD ~1 um), and the "4 / 10 mg/m3 riot / troop"
concentrations have no source read for this model and are not implemented.

## 7. Sources

- DEGADIS User's Manual, Vol I (development) and Vol III (listings),
  Havens & Spicer 1985, USCG-D-24-85, DTIC AD-A171 522 / AD-A171 524.
- Kawamura & Mackay 1987, J. Hazard. Mater. 15(3):343-364; Mackay &
  Matsugu 1973.
- EPA AEGL programme: chlorine, tear gas (CS).
- NIOSH IDLH and Pocket Guide 0122; ACGIH TLV.
- ISO 2533 (standard atmosphere: dry-air molar mass and density).
- CRC Handbook of Chemistry and Physics (chlorine vapour pressure).
