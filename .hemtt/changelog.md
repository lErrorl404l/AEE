# Changelog

## [1.1.1]


### Fixed

- Player thermal bug from the Scottish Highlands report (#123): the four
  `compat_ace3` heat gates read CBA settings with a `0` fallback, which
  fired every gate when the settings were uninitialised. Thresholds now
  resolve once with their real defaults, and the WBGT band cascade no
  longer lets the extreme-caution band overwrite the danger band (#154).
- Biome case-mismatch and latitude inversion (#123): surface keys no
  longer collide with `#GdtGrass` uppercase keys, and the seasonal solar
  curve uses the absolute world latitude instead of the negative value
  from southern-hemisphere maps. Climate normals are now latitude-driven
  from first principles (Köppen classification).
- Rain-on-optics droplets no longer smear across the view (#152): the
  emitter is eye-velocity-cancelling, so droplets stay fixed to the lens.
- Coriolis deflection now reads one shared latitude source instead of
  guessing from map Y, matching the solar model's hemisphere sign (#154).
- Scottish Highlands classified ET/Tundra instead of Dfb (#178): the
  seasonal climate phase was computed in radians and fed to SQF `sin`,
  which takes degrees, collapsing the annual temperature cycle. The three
  call sites now convert the phase to degrees, so high-latitude maps keep
  a real seasonal swing (Dfb, warmest month ~19.6 C on oski_corran).
- ACE3 air temperature read -37 C at altitude (#181): the compat wrote the
  lapse-adjusted temperature into `ace_weather_currentTemperature`, and
  ACE3's `calculateTemperatureAtHeight` applies its own 6.5 C/km lapse,
  so the lapse double-counted. The compat now publishes the un-lapsed base
  temperature and re-asserts `ace_weather_enabled = false` every tick,
  because a mission CBA settings hash can re-enable ACE3's weather model
  after preInit.
- Heat-stress medication stacked without limit: ACE3's
  `addMedicationAdjustment` appends an entry instead of replacing it, so
  re-adding every 5 s tick compounded the vitals adjustment. The compat
  now adds once on the clear-to-hot transition and removes its own entry
  directly on clear.
- Diagnostic density always read `0001` (#177): `CBA_fnc_formatNumber`
  takes `[number, integer width, decimal places]`, and the calls passed
  the decimal width in the integer slot. Fixed at the three call sites.
- Thermal-burn wounds appeared instantly on a night-to-day time skip: the
  burn gate fired every 5 s tick while the air exceeded the threshold, so
  a skip that jumped past 25 C compounded burn damage in a single tick.
  The gate now requires 60 s of sustained exposure before any damage,
  matching the heat-stress transition-guard pattern.

## [1.1.0]


### Added

- Scientific validation harness: grid-comparison of the physics formulas
  against Murphy & Koop 2005, ASHRAE psychrolib, NWS wind-chill values,
  pvlib SPA, and the ISA table.
- Real-world weather input: `compat_realweather` reads a `weather.json`
  written by `tools/weather_fetch.py` (Open-Meteo, no API key).
- ACE3 Kestrel 4500 populated from AEE state; wind-barb follows the
  engine wind AEE drives.
- Zeus/3DEN storm-control module (type, intensity, duration).
- Unit test programme: 183 tests across seven suites mirroring the physics
  models, with reference, edge-case, and monotonicity checks
  (`tools/run_tests.py` single-command runner; pre-commit hook gates on
  the unit tests).
- Dedicated-server integration test: ten-phase headless verification
  (settings, function resolution, state surface, compat gating,
  determinism, module coverage, AI-unit functions, biome resolution,
  edge cases, performance budget).
- Host-compat integration tests: ACE3, ACRE2, TFAR, KAT, and ACM verified
  against the real host mods in a live server (ACM PBO filenames are
  lowercased for the case-sensitive Linux server).
- Coarse WMM magnetic-declination lookup grid for the compass.
- Physics reference checks for the upgraded models: Atlas rain
  extinction, Penman-Monteith evaporation, Cn² seeing, physical smoke
  dispersal, WMO Beaufort sea state, harmonic tides, and the deterministic
  LCG (13 harness checks, 0 skipped with the optional libraries).

### Changed

- Physics models upgraded from simplified approximations to their
  authoritative forms (27 models):
  - Mobility: SAE J1349 density-ratio engine derating, slip-curve
    traction, per-vehicle mud accretion, Nash-cascade river water level,
    NRMM cone-index route degradation.
  - Physiology: FAA time-of-useful-consciousness hypoxia, ISO 17166 UV
    index with ozone absorption, altitude acclimatisation on the 14-day
    timescale, battery derating from 0 °C, scent dispersion unit fixes.
  - Radio: Friis free-space path loss with ducting, ITU-R P.531
    ionospheric absorption (1/f², solar zenith, sunspot).
  - Environmental: Arrhenius Q10 CBRN persistence, Rothermel fire spread,
    Stefan freeze/thaw, corrected avalanche slope curve, intensity-driven
    flash flood, dust-devil wind band, wetting/drying surface-wetness
    balance.
  - Atmos: LWC-based airframe icing, CAPE cloud development, Köhler haze,
    ice-phase lightning, NWS microburst tiers, WMO 3-hour pressure
    tendency, ICAO EDR turbulence, radiational fog, diurnal humidity.
  - Optics: Cn² boundary-layer seeing, physical smoke dispersal chain,
    Atlas rain extinction.
  - Maritime: harmonic tidal prediction (M2/S2/K1/O1), WMO Beaufort sea
    state, Pierson-Moskowitz wave height.
- Precipitation phase determined from the wet-bulb temperature (Stull
  2011), not the dry-bulb — snow forms well above 0 °C in dry air.
- Post-process effects unified under a central arbiter: one owner each
  for ChromAberration, DynamicBlur, and ColorCorrections, with hysteresis
  bands and generation-guarded deferred disables (flicker eliminated).
- Particle effects ported from the `drop` command to `#particlesource`
  with lifecycle management and a source-count budget.
- Weather simulation: `updateWind` runs in real-weather mode too, so the
  wind field does not freeze when real data is active.

### Fixed

- WBGT (Stull 2011) used SQF atan in degrees. The formula needs radians.
- getSunPosition returns nil on a dedicated server (no renderer). Sun
  consumers now guard and fall back cleanly.
- getDirVisual can return NaN for freshly spawned AI. Guarded.
- UV index ozone coefficient was 40× too strong — UV collapsed to zero at
  every realistic ozone level. Corrected coefficient reproduces a UVI of
  ~7 at 60° elevation and 300 DU.
- Friis radio path loss divided the log argument by ln(10) instead of the
  result — the propagation index was dead at its floor. Corrected.
- Coriolis deflection fed radians to a degrees-expecting `sin` — the
  deflection was ~50× too small. Corrected.
- Tidal spring/neap used the wrong trig function with a spurious radian
  conversion — the beat stretched to 846 days. Corrected to the cosine of
  the M2-S2 phase difference.
- Frost on windscreens read a never-written variable name — frost formed
  on overcast nights. Corrected to the actual state variable.
- Pressure trend claimed a 3-hour WMO window but held a two-tick buffer
  (5-second delta). Replaced with a bounded time-stamped 3-hour ring
  buffer.
- `weather.json` values are range-checked at the trust boundary; an
  out-of-range value rejects the whole file instead of corrupting shared
  state.
- Compatibility fixes: ACRE2 signal callback returned percent in the wrong
  scale and applied dB to the percent (now 0..1 with the dB shift applied
  to the dBm value); TFAR used non-existent missionNamespace multipliers
  (now the per-unit `tf_sendingDistanceMultiplicator`, sending only);
  KAT body-fluid writes corrupted the 5-compartment mL array (now the full
  array with compartment drains); ACM no-arg call was dead code and the
  CBRN decay modifier was fed to a 0..100 scale unnormalised (now
  normalised 0..1 with a clamped buildup).
- ACE3 weather ownership: the `ace_weather_enable*` settings are dead in
  ACE3 — its server tick kept overwriting AEE state. `ace_weather_enabled
  = false` removes the tick.
- Dedicated-server runtime errors: `gust` is undefined on a headless
  server (guarded); Coriolis and updateTemperature crash on malformed
  positions and garbage params (now guarded and coerced).

### Removed

- Dead `ace_medical_dehydrationRisk` write (ACE3 has no such variable; it
  polluted the ace_medical_ namespace).
- SQFVM check from CI: its parser is incompatible with CBA-macro code
  (false positives on `getOrDefault`/`keys`/`createHashMap` and config
  syntax); the authoritative validators are the HEMTT lint gate and the
  repo SQF validator.

### Documentation

- Wiki expanded to the current physics surface: new Configuration chapter
  (all 30 CBA settings), Modules and State-variables chapters synced to
  the code, Introduction and Getting Started corrected (19 addons, 6
  compat), Integrations chapter per host mod, and annexes A and C covering
  the 19 upgraded-model formulas and the full state-variable reference.

