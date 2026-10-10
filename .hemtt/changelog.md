# Changelog

## [1.1.1]


> Fixes the defects found in field testing: high-latitude maps now get
> their real seasonal climate instead of Tundra, world latitude feeds
> every consumer from one source, ACE3 air temperature no longer
> double-lapses, heat-stress medication and burn damage no longer stack
> on time skips, and the density readout shows true values.

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
- Latitude climate computed the seasonal phase in radians but fed SQF's
  degree-based `sin`: the annual temperature cycle collapsed, so
  high-latitude maps (Scottish Highlands, lat 56.7) classified as Tundra
  and drove the ambient temperature to freezing (#178). The three `sin`
  calls now convert the phase to degrees, restoring the real seasonal
  curve (Dfb, warmest month 19.6 C).
- ACE3 air temperature read -37 C at altitude (#181): the compat wrote the
  lapse-adjusted temperature into `ace_weather_currentTemperature`, and
  ACE3's `calculateTemperatureAtHeight` applies its own 6.5 C/km lapse,
  so the lapse double-counted. The compat now publishes the un-lapsed
  base temperature and re-asserts `ace_weather_enabled = false` every
  tick, because a mission CBA settings hash can re-enable ACE3's weather
  model after preInit.
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

