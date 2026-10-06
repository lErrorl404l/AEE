# Wildlife Ecology Constant Register

Every tunable value in the wildlife ecology layer, its value, its grade and
its formula. This is the per-constant register the plan task 24 requires.

Grade key:

- **S** sourced to a published relation or standard.
- **S-lit** a sourced literature value.
- **R** derived by a formula from a sourced value.
- **U** an unsourced modelling choice. It is stated so the register holds it.

The kernels are `addons/wildlife/functions/`. The named constants are in
`addons/wildlife/script_component.hpp`. The corpus values are in
`data/wildlife/ecology.json`, generated into `ecology_corpus.sqf`.

## Acoustic propagation (task T25)

`fnc_acousticSourceDb.sqf`, `fnc_acousticLevel.sqf`, `fnc_acousticPublish.sqf`.

| Constant | Value | Grade | Formula or basis |
|---|---|---|---|
| Spherical spreading | 20*log10(d) dB | S | inverse-square law, 6 dB per doubling |
| `WILDLIFE_ACOUSTIC_EVENT_CAP` | 64 | U | event bus cap |
| `WILDLIFE_ACOUSTIC_EVENT_HORIZON` | 3 s | U | event age |
| `WILDLIFE_ACOUSTIC_OCCLUSION_DB` | 6 dB | U | loss per occluder |
| `WILDLIFE_ACOUSTIC_OCCLUSION_RADIUS_M` | 2.5 m | U | line-of-sight tube radius |
| `WILDLIFE_ACOUSTIC_HEARING_FLOOR_DB` | 30 dB | U | stimulus zero |
| `WILDLIFE_ACOUSTIC_LOUD_DB` | 140 dB | U | stimulus one |
| `WILDLIFE_SPOOK_ACOUSTIC_MIN` | 0.5 | U | spook threshold on the stimulus |
| source level: gunshot | 160 dB | U | loudness order |
| source level: suppressed | 120 dB | U | loudness order |
| source level: explosion | 180 dB | U | loudness order |
| source level: grenade | 170 dB | U | loudness order |
| source level: aircraft | 130 dB | U | loudness order |
| source level: vehicle | 100 dB | U | loudness order |
| source level: footstep | 50 dB | U | loudness order |
| stimulus | (level - 30) / 110 | R | from the floor and the loud reference |

The propagation index is `aee_environmental_currentSoundPropagation`, AEE's own
weather model (0.3 to 2.0), not a new constant. It scales the effective range.

## Shot audio (task T26)

`fnc_shotAudio.sqf`.

| Constant | Value | Grade | Formula or basis |
|---|---|---|---|
| Speed of sound | 20.05*sqrt(T_K) m/s | S | dry-air relation, same as the ballistics drag and Mach-cone kernels |
| `WILDLIFE_SHOT_REPORT_DB` | 160 dB | U | report reference level |
| `WILDLIFE_SHOT_REPORT_REF_MV` | 900 m/s | U | reference muzzle velocity |
| `WILDLIFE_SHOT_PITCH_PER_MACH` | 0.15 | U | report pitch slope per Mach |
| `WILDLIFE_SHOT_CRACK_DB` | 150 dB | U | crack reference level |
| crack level slope | 30 dB per Mach | U | crack rise with the Mach excess |
| `WILDLIFE_SHOT_SNAP_RADIUS_M` | 5 m | U | near-pass snap radius |
| `WILDLIFE_SHOT_SNAP_DB` | 140 dB | U | snap reference level |
| `WILDLIFE_SHOT_RICOCHET_DB` | 130 dB | U | ricochet reference level |
| `WILDLIFE_SHOT_RICOCHET_ANGLE_DEG` | 30 deg | U | grazing angle from the surface plane |
| `WILDLIFE_SHOT_RICOCHET_REF_J` | 500 J | U | reference impact energy |
| report source | 160 + 20*log10(mv/900) | R | level from the muzzle velocity |
| report pitch | clamp(1 + 0.15*(Mach-1), 0.5, 2.0) | R | pitch from the muzzle Mach |
| crack gate | Mach_now > 1 | S | supersonic only above Mach 1 in the local air |
| crack level | 150 + 30*(Mach-1) - spread | R | from the crack reference and the spreading |
| snap level | 140*(1 - d/5) | R | linear fall to the snap radius |
| ricochet level | 130 * min(J/500,1) * (1 - angle/30) | R | energy and angle factors |

## Attached emitter (task T27)

`fnc_emitterPlan.sqf`, `fnc_emitterSync.sqf`, `fnc_emitterRelease.sqf`.

| Constant | Value | Grade | Formula or basis |
|---|---|---|---|
| `WILDLIFE_EMITTER_CAP` | 8 | U | live attached emitters |
| `WILDLIFE_EMITTER_RADIUS` | 150 m | U | animals near enough to carry an emitter |

## Call pitch (task T28)

`fnc_callPitch.sqf`.

| Constant | Value | Grade | Formula or basis |
|---|---|---|---|
| Speed of sound | 20.05*sqrt(T_K) m/s | S | dry-air relation |
| Doppler shift | c / (c - v) | S | closing source raises the pitch |
| Doppler clamp | v within 0.9*c | U | keeps the ratio finite |
| `WILDLIFE_PITCH_MIN` | 0.5 | U | lower pitch bound |
| `WILDLIFE_PITCH_MAX` | 2.0 | U | upper pitch bound |
| `WILDLIFE_PITCH_JITTER` | 0.04 | U | per-call pitch spread |
| `WILDLIFE_PITCH_RATE_COUPLING` | 0.25 | U | stridulation pitch coupling |
| Dolbear rate | N = 7*T - 30 chirps/min | S | Dolbear relation |
| stridulation pitch | 1 + 0.25*((7T-30)/110 - 1) | R | coupling to the Dolbear rate |
| stridulation rate reference | 110 chirps/min | U | the 20 C Dolbear value |
| guild pitch: cricket, cicada | stridulator | U | pitch from the temperature |
| guild pitch: frog | 0.95 | U | no body mass held |
| guild pitch: owl | 0.85 | U | no body mass held |
| guild pitch: bird | 1.10 | U | no body mass held |
| guild pitch: deer, wolf | 0.82 | U | no body mass held |
| guild pitch: gull | 1.05 | U | no body mass held |
| guild pitch: hen | 1.02 | U | no body mass held |
| guild pitch: dog | 0.95 | U | no body mass held |
| guild pitch: sheep | 0.92 | U | no body mass held |

## Environment grid

`fnc_sampleNeighbourhood.sqf`, `fnc_environmentGrid.sqf`.

| Constant | Value | Grade | Formula or basis |
|---|---|---|---|
| `WILDLIFE_ENVIRONMENT_QUERY_CAP` | 64 | U | object queries per call |
| `WILDLIFE_ENVIRONMENT_CAP` | 256 | U | cached per-cell samples |
| `WILDLIFE_ENVIRONMENT_HORIZON` | 120 s | U | cache age, mirrors the disturbance field |
| `WILDLIFE_ENVIRONMENT_HALF_LIFE` | 45 s | U | cache decay, mirrors the disturbance field |
| `WILDLIFE_SUITABILITY_MIN` | 0.2 | U | spawn suitability floor |
| cell size | 25 m | U | setting default |
| cells per axis | 5 | U | setting default |
| object cap per cell | 12 | U | setting default |
| sampler budget | 2.0 ms | U | setting default |
| foliage fraction | trees / object cap | R | capped at 1 |
| structure fraction | buildings / object cap | R | capped at 1 |
| surface score | warm votes / total votes | R | cold materials excluded |
| cold materials | concrete, asphalt, metal, glass, water | U | do not warm a basking group |
| suitability | sum(weight*factor) / sum(weight) | R | clamped 0 to 1 |

## Cognition

`fnc_ecologyTick.sqf`, `fnc_ecologyBudget.sqf`, `fnc_wildlifePerceive.sqf`,
`fnc_wildlifeThink.sqf`.

| Constant | Value | Grade | Formula or basis |
|---|---|---|---|
| `WILDLIFE_COGNITION_BATCH` | 8 | U | animals per ecology tick |
| cognition budget | 1.0 ms | U | setting default |
| `WILDLIFE_CALL_RANGE` | 200 m | U | default audibility range |
| `WILDLIFE_CALL_BUDGET` | 256 | U | heard-call bus cap |
| `WILDLIFE_CALL_HORIZON` | 120 s | U | call age |
| `WILDLIFE_CALL_HALF_LIFE` | 45 s | U | call decay |
| perceive: hunger threshold | 0.4 | U | default, overridden by the species rules |
| perceive: thirst threshold | 0.6 | U | default, overridden by the species rules |
| think: flee | 0.7 | U | default, caller overrides |
| think: freeze | 0.3 | U | default, caller overrides |
| think: drink | 0.5 | U | default, caller overrides |
| think: forage | 0.2 | U | default, caller overrides |
| think: boundary | 0.3 | U | default, caller overrides |
| alarm urgency | 0.7*threat + 0.3*gregariousness | U | threat-dominant |
| social urgency | 0.7*gregariousness + 0.3*suitability | U | group-dominant |
| cohesion floor | 0.5 | U | below it no contact call |
| receive: strength | urgency*(1 - d/range) | R | distance attenuation |
| receive: strong threshold | 0.5 | U | flee above it, silent below |

## Sound schedule

`fnc_getCallPattern.sqf`, `fnc_soundTick.sqf`.

| Constant | Value | Grade | Formula or basis |
|---|---|---|---|
| guild rate: songbird | 12 /min | U | modelling choice |
| guild rate: owl | 2 /min | U | modelling choice |
| guild rate: cicada | 30 /min | U | modelling choice |
| guild rate: frog | 20 /min | U | modelling choice |
| guild rate: cricket | 7*T - 30 /min | S | Dolbear relation |
| guild rate: default | 4 /min | U | modelling choice |
| Dolbear valid band | 5 to 30 C | U | outside the band the rate is zero |
| Dolbear normalisation | (N - 5) / 175 | U | maps the band to 0 to 1 |
| time bin edges | 4, 6, 9, 12, 15, 18, 21 | U | hour to corpus bin |
| night sun gate | elevation < -6 deg | U | overrides the bin to night |
| season factor: spring | 1.0 | U | month 3 to 5 |
| season factor: summer | 0.9 | U | month 6 to 8 |
| season factor: autumn | 0.7 | U | month 9 to 11 |
| season factor: winter | 0.5 | U | month 12 to 2 |
| wind suppression | 1 - min(wind/12, 1) | U | linear fall to 12 m/s |
| rain suppression | 1 - 0.4*rain | U | linear fall |
| amphibian rain gate | 0.2 below rain 0.2 | U | a dry hour damps the chorus |
| cicada sun gate | 0 above the horizon | U | diurnal |
| seeded phase | ((seed*31 + g*17) mod 1000)/1000 | U | stable integer count |

## Species match and season

`fnc_getSpeciesMatch.sqf`, `fnc_getSeason.sqf`.

| Constant | Value | Grade | Formula or basis |
|---|---|---|---|
| settlement overlay | structure > 0.35 | U | built-up cue |
| water overlay | water fraction > 0.5 | U | water family cue |
| activity: diurnal gate | elevation > -6 deg | U | true sun elevation |
| activity: nocturnal gate | elevation < 6 deg | U | true sun elevation |
| activity: crepuscular gate | abs(elevation) <= 15 deg | U | true sun elevation |
| temporal bin edges | -6, 0, 15, 40 deg | U | elevation to corpus bin |
| habitat factor | 0.5 + 0.5*pull | U | pull from the group weights |
| seeded jitter | (seed*101 + (i+1)*37) mod 997 | U | 0.25 to 1.0, per group |
| season split | 3-5, 6-8, 9-11 | U | northern four-season split |
| seasonality: tropical | 0.25 | U | little swing |
| seasonality: arid | 0.6 | U | moderate swing |
| seasonality: other | 1.0 | U | full swing |
| boundary exception rate | 0.02 | U | rare seeded excursion |
| boundary hash | (seed*101 + 37) mod 997 | U | deterministic roll |

## Pre-existing ambience constants

These predate the ecology layer and are unchanged. They are held in the
wildlife-ambience dossier.

| Constant | Value | Grade | Formula or basis |
|---|---|---|---|
| `WILDLIFE_SOUND_INSTANCE_CAP` | 8 | U | live one-shots |
| `WILDLIFE_SOUND_MAX_DISTANCE` | 120 m | U | one-shot range |
| `WILDLIFE_ANIMAL_CAP` | 16 | U | live animals |
