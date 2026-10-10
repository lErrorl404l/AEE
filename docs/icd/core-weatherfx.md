# ICD: core to weatherfx

- Producer CI: `addons/core/`
- Consumer CI: `addons/weatherfx/`
- Direction: one way. `core` must initialise before `weatherfx` reads.
- Variables crossing: 16.

A variable named `aee_core_{leaf}` is written as `EGVAR(core,leaf)` by the producer and read as `EGVAR(core,leaf)` or `QEGVAR(core,leaf)` by the consumer.

| Variable | Type | Unit | Range | Update | Evidence (first read) | Purpose (Annex C) |
|---|---|---|---|---|---|---|
| `aee_core_atmosphericEventsEnabled` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/weatherfx/functions/weather/fnc_triggerLightning.sqf:14` | UNKNOWN |
| `aee_core_currentAirDensity` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/weatherfx/functions/weather/fnc_applyExhaustShimmer.sqf:301` | Air density in kg/m3 |
| `aee_core_currentBlowingSnow` | SCALAR | fraction | 0..1 | UNKNOWN | `addons/weatherfx/functions/weather/fnc_triggerSevereWeatherFX.sqf:17` | Blowing snow 0..1 |
| `aee_core_currentDustDevil` | SCALAR | fraction | 0..1 | UNKNOWN | `addons/weatherfx/functions/weather/fnc_triggerSevereWeatherFX.sqf:18` | Dust devil activity 0..1 |
| `aee_core_currentLightningRisk` | SCALAR | fraction | 0..1 | UNKNOWN | `addons/weatherfx/functions/weather/fnc_triggerLightning.sqf:22` | Lightning risk 0..1 |
| `aee_core_currentSandstorm` | SCALAR | fraction | 0..1 | UNKNOWN | `addons/weatherfx/functions/weather/fnc_applyWeatherParticles.sqf:76` | Sandstorm intensity 0..1 |
| `aee_core_currentTemperature` | SCALAR | degrees C | UNKNOWN | UNKNOWN | `addons/weatherfx/functions/weather/fnc_applyBreathCondensation.sqf:16` | Air temperature in C |
| `aee_core_currentWindStr` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/weatherfx/functions/weather/fnc_applyAtmosphericDust.sqf:29` | UNKNOWN |
| `aee_core_dustSuppression` | SCALAR | fraction | 0..1 | UNKNOWN | `addons/weatherfx/functions/weather/fnc_applyFootfallDust.sqf:39` | Dust suppression 0..1 |
| `aee_core_enabled` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/weatherfx/functions/weather/fnc_applyAtmosphericDust.sqf:17` | Master switch |
| `aee_core_environmentalEnabled` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/weatherfx/functions/weather/fnc_applyBreathCondensation.sqf:14` | UNKNOWN |
| `aee_core_lastStrikePos` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/weatherfx/functions/weather/fnc_calculateLightningStrikeEffects.sqf:22` | Last lightning strike position |
| `aee_core_lightningIgnition` | BOOL | boolean | 0 or 1 | UNKNOWN | `addons/weatherfx/functions/weather/fnc_calculateLightningStrikeEffects.sqf:21` | Lightning ignition flag |
| `aee_core_opticsEnabled` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/weatherfx/functions/weather/fnc_applyExhaustShimmer.sqf:211` | UNKNOWN |
| `aee_core_precipitationPhase` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/weatherfx/functions/weather/fnc_applyWeatherParticles.sqf:37` | Phase (rain/sleet/snow/freezing_rain) |
| `aee_core_updateInterval` | SCALAR | s | UNKNOWN | UNKNOWN | `addons/weatherfx/functions/weather/fnc_triggerLightning.sqf:17` | Update interval in seconds |

The default value and the update frequency are the producer's contract. They are set in the producer's CBA settings and recorded in `docs/wiki/annexes/annex-c-variable-reference.qmd`. This document records the boundary and the direction, not a second copy of the variable reference.

Regenerate with `python3 tools/architecture/interface_contracts.py`.
