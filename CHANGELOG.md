# Changelog

All notable changes to this project are documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versioning follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.0] - 2026-09-15

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

## [1.0.0] - 2026-09-11

### Added

- CBA utilisation: standalone keybinds for the actions, a
  `AEE_WeatherUpdated` local event after every tick, and player-killed
  handling that resets heat acclimatisation.
- Solar-radiation diurnal model: the temperature curve follows the sun's
  elevation (date, time, latitude) with cloud transmission, replacing the
  fixed sinusoid.
- Soil moisture and evaporation: rain soaks the ground, warm and windy air
  dries it, and moist soil raises the relative humidity (water cycle).
- Deterministic event state: lightning, microburst, and space-weather rolls
  use a seeded LCG so all machines agree on event state.
- Thunder follows the flash: the sound rolls arrive after a fixed delay.
- AI-player test: the headless mission spawns an AI unit and exercises the
  unit-dependent optics and ballistics functions.
- Map rotation test: runs Stratis, Tanoa, and Enoch and asserts each world
  resolves to its Koppen biome.
- Module-coverage phase: verifies the state surface of every subsystem.

### Fixed

- WBGT (Stull 2011) used SQF atan in degrees. the formula needs radians.
- getSunPosition returns nil on a dedicated server (no renderer). sun
  consumers now guard and fall back cleanly.
- getDirVisual can return NaN for freshly spawned AI. guarded.

## [0.1.0] - 2026-09-11

### Added

- Modular restructure: 18 addons (core, atmos, thermal, ballistics, optics,
  mobility, environmental, maritime, physiology, radio, fx, actions, main,
  and 5 compat addons).
- Canonical ACE3/CBA function wiring in every addon (XEH_PREP, four-link
  XEH chain, functions/fnc_<name>.sqf).
- Component-scoped naming: functions `aee_<component>_fnc_<name>`, state in
  `aee_core_*` mission variables.
- Settings registered with `CBA_fnc_addSetting`, titles in stringtables.
- Standalone core: no ACE3 dependency. Compat addons gate on their host mod
  with `skipWhenMissingDependencies`.
- Deterministic multiplayer state: core atmospheric values are a pure
  function of position, mission time, and engine weather.
- EDEN module (AEE Environment Config).
- Headless dedicated-server test harness (`tools/docker_test.sh`) with a
  five-phase verification mission and baseline-vs-patched comparison.
- Physics reference checks (`tools/tests/test_physics.py`).
- CI: pedantic HEMTT lint gate, SQF validation, SQFVM, stringtable checks,
  SBOM on release tags, release-drafter, dependant bots.
- Licence: GPL-2.0-or-later with a PBO-distribution exception.

### Fixed

- Function compilation: no function was compiled before this release. the
  mod did not run. Wiring now resolves every function (zero undefined).
- ACE3 bridge: removed the fake `ace_weather_current*` variable interface.
  AEE drives engine weather; ACE3 reads engine state.
- Dedicated-server runtime errors found by the headless test: unit params
  default to objNull, bare `call` no longer inherits the caller's `_this`,
  and biome state is written to the core namespace.
- Missing assets: logo references removed from mod.cpp.

[1.0.0]: https://github.com/lErrorl404l/AEE/releases/tag/v1.0.0
[0.1.0]: https://github.com/lErrorl404l/AEE/releases/tag/v0.1.0