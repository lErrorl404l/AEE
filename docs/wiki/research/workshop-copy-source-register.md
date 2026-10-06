# Workshop Copy Source Register

This register records the source of every idea that AEE re-implements from the
Workshop mods surveyed for the `aee-workshop-copy` plan. It holds one row per
item. No mod publishes a licence, so AEE copies no code, array, texture or
content. AEE re-derives each numeric constant or re-implements each kernel
against its own patterns. The base game config is read at run time and is
never shipped.

The State column marks an item that ships. All ten items now ship or are
recorded.

| Item | Value or behaviour | Source mod | Workshop id | Licence | AEE target file | State |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | Complete `HDRNewPars`: bloom, tonemap, eye adaptation and night shift | Real Lighting and Weather | 2809399991 | no licence published; re-implemented, not copied | `addons/environmental/config.cpp` | implemented |
| 2 | `starEmissivity` 40 as the shared default in the world class chain, and a run-time matcher that classifies every world from latitude, biome, terrain and weather, with no per-map entry | Fluffys (30) and Real Lighting and Weather (60) | 3704702374, 3737586377, 2809399991 | no licence published; re-implemented, not copied | `addons/environmental/config.cpp`, `addons/environmental/functions/lighting/` | implemented |
| 3 | Star Light brightness coefficient: moon phase, ambient brightness, house count, overcast and fog fades | Star Light (PLP star sphere) | 3749362906 | no licence published; re-implemented, not copied | `addons/environmental/functions/astronomy/fnc_starBrightnessCoefficient.sqf`, `fnc_starWeatherFade.sqf`, `fnc_lightPollutionPenalty.sqf`, `fnc_calculateLimitingMagnitude.sqf`, `fnc_getStarCatalog.sqf`, `fnc_starMagnitude.sqf` | implemented |
| 4 | `DayLighting` `deepNight` and `fullNight` night-darkness endpoints | Real Lighting and Weather | 2809399991 | no licence published; re-implemented, not copied | `addons/environmental/config.cpp` | implemented |
| 5 | Rain-scaled film grain, colour element 1 | Real Lighting and Weather (RW_Effects) | 2809399991 | no licence published; re-implemented, not copied | `addons/optics/functions/vision/fnc_weatherGrainParams.sqf`, `fnc_applyWeatherGrain.sqf`, `fnc_initWeatherGrain.sqf` | implemented |
| 6 | Scene-aware shadow distance: screen sample, classifier, margins, FPS governor | Adaptive Shadows | 3792830104 | no licence published; re-implemented, not copied | `addons/optics/functions/vision/fnc_shadowSamplePattern.sqf`, `fnc_shadowClassifyScene.sqf`, `fnc_shadowTargetDistance.sqf`, `fnc_shadowSmoothDistance.sqf`, `fnc_shadowFpsGovernor.sqf`, `fnc_shadowStabilizeDepth.sqf`, `fnc_calculateViewDistance.sqf` | implemented |
| 7 | Weather particle alpha and ambient-temperature heat haze | Better Visuals | 3351805137 | no licence published; re-implemented, not copied | `addons/fx/functions/particle/fnc_weatherParticleAlpha.sqf`, `fnc_heatHazeAlpha.sqf`, `fnc_heatHazeSize.sqf`, `addons/fx/functions/weather/fnc_applyExhaustShimmer.sqf` | implemented |
| 8 | FilmGrain colour invariant and IR-laser daylight alpha | Enhanced Visuals | 880703327 | no licence published; re-implemented, not copied | `addons/nightvision/functions/ltm/fnc_ltmDaylightAlpha.sqf`, `fnc_ltmDraw.sqf` and the FilmGrain arrays across addons | implemented |
| 9 | Video-option ceiling review (document only) | Enhanced Video Settings | 1223309664 | no licence published; re-implemented, not copied | `docs/wiki/research/video-option-ceiling.md` | implemented |
| 10 | Post-process template reference (document only) | Post Process Effects | 656307117 | no licence published; re-implemented, not copied | `docs/wiki/research/post-process-template-reference.md` | implemented |

`starEmissivity` 40 is the shared default in the world class chain. The matcher
classifies every world from biome, latitude, terrain and weather. It keys no
value by a map name. Items 1, 2 and 4 ship in the Phase 1 engine config. Item 9
and item 10 are documentation only. The full decisions are in ADR-016.
