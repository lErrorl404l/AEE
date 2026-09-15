# Changelog

## [1.0.0]


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

