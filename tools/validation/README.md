# Physics Validation Harness

This directory validates the atmospheric physics formulas in the AEE mod
against published references. The script mirrors each SQF implementation
exactly, then compares it with a ground-truth source.

The script runs without network access. All references are implemented
locally in the script or in the optional libraries below.

## Run

```bash
# Full harness (all 13 checks, requires the venv for optional libraries)
tools/validation/.venv/bin/python tools/validation/validate_physics.py

# Core path only (standard library, skips the 3 optional-library checks)
python3 tools/validation/validate_physics.py
echo $?
```

The exit code is 0 when every run check passes. It is 1 when any check
fails. The script writes the full report to `tools/validation/report.txt`.

The core path uses only the Python standard library. Three optional
libraries add checks. When a library is absent, its check is skipped with a
clear message. A skip does not change the exit code. A project venv with
all optional libraries is provided at `.venv` (created with `uv`):

```bash
cd tools/validation && uv venv .venv
uv pip install --python .venv/bin/python psychrolib metpy pvlib pandas
```

| Library | Check it enables | Install |
|---|---|---|
| psychrolib | Wet bulb (Stull 2011 vs ASHRAE) | `pip install psychrolib` |
| metpy | ISA table cross-check | `pip install metpy` |
| pvlib | Solar position (mod vs SPA) | `pip install pvlib` |

## Formulas and tolerances

### 1. Saturation vapour pressure (Buck 1996)

Source: `addons/ballistics/functions/fnc_calculateAirDensity.sqf`.

The mod uses the Buck 1996 enhancement formula:

```
e_s = 6.1121 * exp((18.678 - T/234.5) * T / (257.14 + T))
```

T is in Celsius, e_s is in hPa.

Ground truth: Murphy & Koop 2005, "Review of the vapour pressures of ice
and supercooled water for atmospheric applications", J. Chem. Phys. 122,
104503. The reference is implemented locally:

```
ln(e_w) = 54.842763 - 6763.22/T - 4.21*ln(T) + 0.000367*T
          + tanh(0.0415*(T-218.8)) * (53.878 - 1331.22/T
          - 9.44523*ln(T) + 0.014025*T)
```

T is in Kelvin, e_w is in Pa.

Grid: T = -40 to 50 C, step 1 C. The Buck result is converted from hPa to
Pa before comparison.

Tolerance: 0.5% relative. The measured error band is 0.00 to 0.35%.

### 2. Wet bulb (Stull 2011)

Source: `addons/thermal/functions/fnc_calculateWBGT.sqf`.

The mod uses the Stull 2011 approximation:

```
Tw = T*atan(0.151977*sqrt(RH+8.313659)) + atan(T+RH) - atan(RH-1.676331)
     + 0.00391838*RH^1.5*atan(0.023101*RH) - 4.686035
```

T is in Celsius, RH in percent, Tw in Celsius.

Radian pitfall: SQF `atan` returns degrees. The mod multiplies each `atan`
term by 0.0174532925 to convert to radians. The Python mirror keeps this
factor so the arithmetic matches the SQF exactly.

Ground truth: psychrolib `GetTWetBulbFromHumRatio`, the ASHRAE iterative
method, at 101.325 kPa. psychrolib SI uses Pa for pressure, so the script
passes 101325 Pa.

Grid: T = 0 to 40 C step 5, RH = 10 to 100% step 10.

Tolerance: 1.0 C. The grid is restricted to the range where Stull 2011
holds its stated 1 C accuracy. Outside this range the error grows: the
measured error reaches 3.9 C at T = -20 C, RH = 5%. The grid covers the
heat-stress range where the mod's WBGT is operationally relevant.

Skip-conditional: this check needs psychrolib.

### 3. Wind chill (JAG/TTI)

Source: `addons/thermal/functions/fnc_updateTemperature.sqf`.

The mod uses the NWS/Environment Canada JAG/TTI metric formula:

```
Twc = 13.12 + 0.6215*T - 11.37*(V*3.6)^0.16 + 0.3965*T*(V*3.6)^0.16
```

T is in Celsius, V in m/s (converted to km/h), Twc in Celsius. The result
is clamped to the ambient temperature, as the SQF does.

Ground truth: NWS wind chill calculator outputs. The script embeds a small
table of published values:

| T (C) | V (m/s) | NWS wind chill (C) |
|---|---|---|
| 5 | 2 | 3.4 |
| -10 | 5 | -17.8 |
| 0 | 10 | -6.7 |

The NWS calculator uses the same JAG/TTI formula, so this check validates
the mod against published outputs, not against a second implementation.

Tolerance: 0.5 C. The tolerance covers the rounding of the NWS calculator
outputs. The measured error is at most 0.35 C.

### 4. Solar position

Source: `addons/core/functions/fnc_calculateSolarRadiation.sqf`.

The mod computes the radiation factor:

```
decl = 23.45 * sin((360/365) * (doy + 284))
hourAngle = (hour - 12) * 15
sinElev = sin(lat)*sin(decl) + cos(lat)*cos(decl)*cos(hourAngle)
radiation = max(0, sinElev) * (1 - 0.75*overcast)
```

doy is the exact day of year (Bauleova formula) `floor(275*m/9) - 2*floor((m+9)/12) + d - 30` with a leap-year correction, hour is the local clock hour, lat is in degrees.

Ground truth: pvlib `solar_position`, the SPA algorithm of Reda & Andreas
2004. The comparison uses longitude 0 and UTC so the local clock hour
equals the UTC hour, matching the mod's hour-angle model.

Grid: months 1/4/7/10, days 1/15, hours 6 to 18, latitudes -60 to 60.

This check is informational. The mod uses the Cooper declination formula
and omits the equation of time, so a discrepancy is expected. The measured
max error is 0.06 in radiation units (about 3.5 degrees of elevation).

Skip-conditional: this check needs pvlib.

### 5. Air density vs ISA table

Source: `addons/ballistics/functions/fnc_calculateAirDensity.sqf`.

The mod computes density from temperature, pressure, and humidity:

```
e_s = Buck 1996 (hPa)
e = e_s * RH / 100
T_v = (T + 273.15) / (1 - 0.37802 * e / P_hPa)
rho = (P_hPa * 100) / (287.05287 * T_v)
```

Ground truth: the ICAO standard atmosphere table at 0, 1000, 2000, 5000,
and 11000 m. The script embeds the published values:

| z (m) | T (C) | P (hPa) | rho (kg/m^3) |
|---|---|---|---|
| 0 | 15.0 | 1013.25 | 1.225 |
| 1000 | 8.5 | 898.76 | 1.112 |
| 2000 | 2.0 | 795.01 | 1.007 |
| 5000 | -17.5 | 540.48 | 0.736 |
| 11000 | -56.5 | 226.32 | 0.364 |

The check uses RH = 0 (dry air), so the mod formula reduces to the ideal
gas law. The measured error is at most 0.07%.

Tolerance: 0.5% relative.

### 6. Standard-atmosphere lapse rate

Source: `addons/thermal/functions/fnc_updateTemperature.sqf`.

The mod applies the lapse:

```
T(z) = T_base - 0.0065 * z
```

Ground truth: the temperature column of the ISA table above.

Grid: z = 0, 1000, 2000, 5000, 11000 m.

Tolerance: 0.1 C. The formula reproduces the table exactly.

### 7. WBGT vs ISO 7243

Source: `addons/thermal/functions/fnc_calculateWBGT.sqf`.

The mod computes:

```
WBGT = 0.7*Tw + 0.2*Tg + 0.1*T
Tg = T + 15 * (1 - overcast)
```

Ground truth: ISO 7243. When Tg = Ta, the formula reduces to
`WBGT = 0.7*Tw + 0.3*Ta`. The mod reaches this case at overcast = 1.

Grid: T = 0 to 40 C step 10, RH = 20 to 100% step 20, overcast = 1.

Tolerance: 1e-6 C. The reduction is exact by construction.

### 7b. Heat index (NWS Rothfusz 1990)

Source: `addons/thermal/functions/fnc_calculateHeatIndex.sqf`.

The mod uses the NOAA SR-90-23 Rothfusz regression (with simple form and
low/high-RH adjustments) to compute apparent temperature:

```
HI = -42.379 + 2.04901523*T + 10.14333127*RH - 0.22475541*T*RH
     - 6.83783e-3*T^2 - 5.481717e-2*RH^2 + 1.22874e-3*T^2*RH
     + 8.5282e-4*T*RH^2 - 1.99e-6*T^2*RH^2
```

T and HI are in Fahrenheit (converted internally; the function stores
Celsius). Below 80 F or below 40% RH the simple form
`HI = 0.5*(T + 61 + (T-68)*1.2 + RH*0.094)` applies.

Ground truth: published NWS heat index chart values.

Grid: 5 reference points: (80 F/40 %), (80 F/60 %), (90 F/60 %),
(90 F/70 %), (100 F/40 %).

Tolerance: 1.0 F. The measured max error is 0.88 F, within chart rounding.

### 8. ISA table vs metpy (cross-check)

This check validates the embedded ISA table, not the mod. It compares the
pressure column against `metpy.calc.height_to_pressure_std`.

Tolerance: 0.5% relative. The measured error is at most 0.09%.

Skip-conditional: this check needs metpy.

### 9. Rain visibility (Atlas 1954)

Source: `addons/optics/functions/fnc_calculatePrecipitationVisibility.sqf`.

The mod uses the Atlas & Bartnoff (1954) extinction power law:

```
σ = 0.21 · R^0.74   (km⁻¹), R in mm/h
V = 3.912 / σ       (km, Koschmieder)
```

The harness compares the extinction coefficient against published Atlas
values at R = 2.5, 12.5, 25 mm/h. Tolerance 0.15 km⁻¹. Measured max
error 0.13 km⁻¹.

### 10. Evaporation (Penman-Monteith)

Source: `addons/core/functions/fnc_updateSoilMoisture.sqf`.

The mod uses the FAO-56 Penman-Monteith reference evapotranspiration form.
The mod scales solar radiation to 0..1, so absolute FAO-56 mm/h values do
not apply. The check validates physical behaviour instead: hot-dry-windy
evaporates more than cool-humid-calm, and temperature, wind, dryness, and
sun each raise ET0 monotonically.

### 11. Atmospheric seeing (Cn² model)

Source: `addons/optics/functions/fnc_calculateAtmosphericSeeing.sqf`.

The mod maps boundary-layer Cn² to a seeing index 0.1..1.0. The check
verifies four climate cases land in published behaviour ranges: cold
clear night (excellent), mild overcast day, hot clear day, stormy day.
Tolerance 0.05 index.

### 12. Smoke dispersal (physical model)

Source: `addons/optics/functions/fnc_calculateSmokePersistence.sqf`.

The mod chains advection, Taylor diffusion, Köhler hygroscopic growth,
buoyancy, and rain scavenging. The check verifies calm-humid-cold
persists (>1.0), windy-hot-dry-rain disperses (<0.5), and neutral
conditions stay near 1.0. Tolerance 0.1 modifier.

## How to add a formula

1. Add a mirror function next to the other SQF mirrors. Name it after the
   SQF function it mirrors. Keep the units and the radian factor identical
   to the SQF.
2. Add a reference function in the references section. Implement it
   locally. Do not call a network service.
3. Add a check function that returns a result dict. The dict needs these
   keys: `name`, `ground_truth`, `grid`, `tolerance`, `status`, `max_abs`,
   `rmse`, `unit`, and an optional `note`.
4. Add the check to the `checks` list in `main()`.
5. Document the formula, its reference, and its tolerance in this file.

The status values are `PASS`, `FAIL`, `SKIP`, and `INFO`. A `FAIL` makes
the exit code 1. A `SKIP` or `INFO` does not.

## Notes on units

The mod uses hPa for pressure and Celsius for temperature. The references
use Pa and Kelvin. The script converts at the comparison boundary:

- Buck 1996 gives hPa. Murphy & Koop give Pa. The script multiplies the
  Buck result by 100 before comparing.
- psychrolib SI uses Pa for pressure. The script passes 101325 Pa for
  101.325 kPa.
- The ISA table stores hPa. The mod formula converts to Pa internally.
## Sensor pipeline (NVG/Thermal)

`validate_sensors.py` mirrors the physics equations in
`addons/optics/functions/fnc_applyNVGTubeModel.sqf` and validates them
against published references.  It uses only the Python standard library.

### 13. AGC gain (inverse-lux)

Source: `fnc_applyNVGTubeModel.sqf` lines 233-234.

```
gain = min(sensitivity / (lux + 1), sensitivity)
```

Real AGC reduces gain inversely with input illuminance until the MOB
clamp (Elbit MX-10160: 2.8-4.2 fL held across 1-20 fc input; US4952793A
auto-gating patent).  Check verifies the exact formula and the ~1.25x
gain ratio across the 0.001-0.25 lux moon range.

### 14. Shot noise (Poisson)

Source: lines 252-254.

```
noise = noise_floor + (1 - noise_floor) * 1/sqrt(N+1),  N = lux*sensitivity
```

Photon arrival is Poisson: SNR = sqrt(N).  Check verifies the ratio
between starlight and full-moon noise is sqrt((N_moon+1)/(N_star+1)).

### 15. Temperature gain rolloff (MIL-PRF-49428F)

Source: lines 202-205.

Peaks at 20 C (1.0), falls to 0.7 at -30 C (cathode/MCP gain loss) and
0.85 at 45 C (thermal saturation).  MIL-PRF-49428F operating range
-51..+49 C with reduced performance at the extremes.

### 16. Brightness mapping

Source: line 362.

```
brightness = linearConversion [0.001, 0.25, lux, 0.65, 1.0, true]
```

1.0 = unchanged (BIS wiki anchor), 0.65 = ACE3-proven visible floor.
Check verifies monotonic rise with lux, bounded 0.65..1.0.

### 17. MTF degradation + BSP gating penalty

Source: lines 334-337.

```
mtf = linearConversion [0, 1, noise, mtf15, mtf15*0.55, true]
if gating: mtf *= (1 - blowout * 0.4)
```

Resolution fades to 55% at high noise; Bright Spot Protection reduces
gated-tube (Gen 3/PVS-31) resolution up to 40% while a bright source is
in view (Cold Harbour NV terminology).

## Sensor and illuminance harnesses

Additional stdlib-only harnesses guard the optics/sensor layer:

```bash
# NVG/thermal physics (AGC, shot noise, MTF, temperature, value audit)
python3 tools/validation/validate_sensors.py

# Shared illuminance layer (azimuth/elevation conversion, lux bounds,
# shared-state contract)
python3 tools/validation/validate_illuminance.py

# Astronomical models (lunar illuminance vs Krisciunas & Schaefer 1991,
# NELM vs Garstang/Bortle, DEF Stan 61-027 night classification)
python3 tools/validation/validate_astronomical.py

# CBA settings cross-reference (reads no addon produces, wrong addon
# prefix, dead settings, orphan writes)
python3 tools/validation/validate_cba_settings.py
```

All run with only the Python standard library, exit 0 on pass, and are
wired into `.githooks/pre-commit` and `.github/workflows/ci.yml`.

## Oracle validation (JSP 939 VV&A)

`validate_oracles.py` is the VALIDATION layer (formula matches reality as an
integrated system) on top of `validate_physics.py`'s VERIFICATION (code
matches formula).  Per JSP 939 Modelling & Simulation practice, tolerance
bands are the acceptance criteria.

| Check | Oracle | Tolerance | Optional lib |
|---|---|---|---|
| ISO 9613-1 atmospheric absorption | standard formula, corrected refs 2.60/12.59 dB/km (issue #80) | 0.05 dB/km | none |
| Air density vs ICAO Std Atm | Doc 7488 / ISO 2533 table | 0.5 % rel | none |
| NWS heat index | official 90 F/70 % -> 105.9 F check value | 0.5 F | none |
| WBGT weighting | pythermalcomfort ISO 7243 wbgt() | 0.06 C | pythermalcomfort (SKIP when absent) |

Notes:
- The ISO 9613-1 check guards the issue #80 defect: the original
  hand-computed references (4.164 / 130.217 dB/km) were wrong; the
  verified values are 2.60 / 12.59 dB/km.  The oracle formula uses the
  water-vapour fraction (not percent) in the relaxation frequencies.
- The wet-bulb-vs-psychrolib and ISA-vs-metpy oracles already live in
  `validate_physics.py` (checks #2 and #7) and are not duplicated here.
- pythermalcomfort's wet-bulb is itself Stull, so the WBGT check shares
  the Tw input and validates the 0.7/0.2/0.1 aggregation at overcast=1
  (the mod's ISO 7243 Tg=Ta reduction).

Run with the optional oracle library:

```bash
tools/validation/.venv/bin/python tools/validation/validate_oracles.py
```

## CBA settings validator

`validate_cba_settings.py` scans every `.sqf` in `addons/` and resolves
the `GVAR/QGVAR/EGVAR/QEGVAR` macros against the owning addon.  It
reports four classes:

| Class | Meaning | Fatal by default |
|---|---|---|
| WRONG PREFIX | read as `aee_X_n`, only `aee_Y_n` is produced | yes |
| DEAD READ | read as `aee_X_n`, nothing produces leaf `n` | yes |
| STALE TEST | docker test reads `aee_X_n` that no addon produces and the test does not seed | yes |
| UNDOCUMENTED | orphan write not listed in Annex C | yes |
| DEAD SETTING | declared with `CBA_fnc_addSetting`, never read | no (use `--strict`) |
| ORPHAN WRITE | written, never read | no (use `--strict`) |

The docker test missions (`tests/docker/missions/`) are scanned for literal
variable reads.  A test read that resolves against neither addon-produced
state nor the test's own seeds is a stale assertion: the producer was
renamed and the test was not updated.  This class was a real defect
(`aee_mobility_currentWaterLevel` in PHASE20, fixed in #83).

Intentional knobs (debug console toggles, test override hooks, producers
tracked by another issue) live in `cba_settings_allowlist.txt`; the
validator reports them as ALLOWED and they do not fail the build.  Remove
a line when its producer lands.  Template writes like
`format [QGVAR(ppHandle_%1), _name]` are resolved as dynamic prefixes, so
dynamically-created variables are not false-flagged.
