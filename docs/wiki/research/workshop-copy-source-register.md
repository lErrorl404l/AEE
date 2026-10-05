# Workshop Copy Source Register

This register records the source of every idea that AEE re-implements from the
Workshop mods surveyed for the `aee-workshop-copy` plan. It holds one row per
item. No mod publishes a licence, so AEE copies no code, array, texture or
content. AEE re-derives each numeric constant or re-implements each kernel
against its own patterns. The base game config is read at run time and is
never shipped.

The State column marks an item that does not yet ship. Those rows carry the
source and the intended target file.

| Item | Value or behaviour | Source mod | Workshop id | Licence | AEE target file | State |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | Complete `HDRNewPars`: bloom, tonemap, eye adaptation and night shift | Real Lighting and Weather | 2809399991 | no licence published; re-implemented, not copied | `addons/environmental/config.cpp` | implemented |
| 2 | `starEmissivity` 40, mid-band between 30 and 60 | Fluffys (30) and Real Lighting and Weather (60) | 3704702374, 3737586377, 2809399991 | no licence published; re-implemented, not copied | `addons/environmental/config.cpp` | implemented |
| 3 | Star Light brightness coefficient: moon phase, ambient brightness, house count, overcast and fog fades | Star Light (PLP star sphere) | 3749362906 | no licence published; re-implemented, not copied | `addons/environmental/functions/astronomy/fnc_calculateLimitingMagnitude.sqf`, `fnc_getStarCatalog.sqf`, `fnc_starMagnitude.sqf` | not implemented |
| 4 | `DayLighting` `deepNight` and `fullNight` night-darkness endpoints | Real Lighting and Weather | 2809399991 | no licence published; re-implemented, not copied | `addons/environmental/config.cpp` | implemented |
| 5 | Rain-scaled film grain, colour element 1 | Real Lighting and Weather (RW_Effects) | 2809399991 | no licence published; re-implemented, not copied | `addons/optics/functions/vision/fnc_weatherGrainParams.sqf`, `fnc_ppEffectCreate.sqf` | not implemented |
| 6 | Scene-aware shadow distance: screen sample, classifier, margins, FPS governor | Adaptive Shadows | 3792830104 | no licence published; re-implemented, not copied | `addons/optics/functions/vision/fnc_calculateViewDistance.sqf` | not implemented |
| 7 | Weather particle alpha and ambient-temperature heat haze | Better Visuals | 3351805137 | no licence published; re-implemented, not copied | `addons/fx/functions/particle/`, `addons/fx/functions/weather/fnc_applyExhaustShimmer.sqf` | not implemented |
| 8 | FilmGrain colour invariant and IR-laser daylight alpha | Enhanced Visuals | 880703327 | no licence published; re-implemented, not copied | `addons/nightvision/functions/ltm/fnc_ltmDraw.sqf` and the FilmGrain arrays across addons | not implemented |
| 9 | Video-option ceiling review (document only) | Enhanced Video Settings | 1223309664 | no licence published; re-implemented, not copied | `docs/wiki/research/video-option-ceiling.md` | not implemented |
| 10 | Post-process template reference (document only) | Post Process Effects | 656307117 | no licence published; re-implemented, not copied | `docs/wiki/research/post-process-template-reference.md` | not implemented |

Items 1, 2 and 4 ship in the Phase 1 engine config. Items 3 and 5 to 10 are
recorded here for the later phases, which update this register when they land.
