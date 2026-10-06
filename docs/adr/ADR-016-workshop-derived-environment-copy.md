# ADR-016: Workshop-Derived Environment Copy

Status: Accepted
Date: 2026-10-06
Decision: AEE re-implements the environment, optics and effects ideas from the
eleven Workshop mods surveyed for `aee-workshop-copy` as its own behaviour. AEE
copies no content (textures, sky paths, models); numeric parameter arrays are
re-derived and disclosed in each kernel header. AEE ships no base-game config
data. AEE re-homes the engine config anchor into the world class chain at load
time and reads the base-game config at run time. A world lighting matcher
classifies every world from published facts and drives the run-time levers the
engine exposes. This record supersedes the "not implemented" follow-up in
`human-vision-model.md`.

## Context

The operator asked for the visual and environmental ideas of eleven Workshop
mods inside AEE, for every map, including custom and unknown maps. The surveyed
mods publish no licence. A direct copy is not available and not wanted.

The plan `aee-workshop-copy` holds ten items. Eight change behaviour. Two are
documentation only. The note `engine-hdr-and-night-ceiling.md` records the
engine HDR and night ceiling. The note `video-option-ceiling.md` records the
video-option ceiling. The note `post-process-template-reference.md` records the
post-process templates.

## Licence stance

No surveyed mod publishes a licence. AEE therefore copies no content
(textures, sky paths, models) and no PBO content. Numeric parameter arrays are
re-derived and disclosed in each kernel header. AEE re-implements each kernel
against its own patterns. AEE reads the base-game config at run time and never
ships base-game config data.

Each value in the source register carries the source mod, the Workshop id and
the line "no licence published; re-implemented, not copied". A value with no
published source is marked UNSOURCED beside the value in code.

## The world class chain

The central finding is that a direct child class is inert. A block such as
`class CfgWorlds { class HDRNewPars {...}; }` adds an unreferenced sibling. The
engine reads `HDRNewPars`, `DOFPars`, `Lighting` and the `DayLighting` keyframes
through the world class chain:

`CfgWorlds >> DefaultWorld >> CAWorld >> <World>:CAWorld`

AEE re-homes the anchor into `CAWorld` and into every stock world that
re-declares the class: `Stratis`, `Altis`, `Malden`, `Tanoa` and `Enoch`. Each
block uses the explicit base form `class X: X`. The engine then merges the
values. A declaration without the base form replaces the class and discards the
base values.

Every block carries the same values. This is the engine structural
requirement, not per-map tuning. No value is keyed by a map name.

`starEmissivity` 25 is the shared default. The engine core declares
`DefaultLighting` with `starEmissivity` 0.3. A re-open of `DefaultLighting`
merges and propagates. A world that sets its own `starEmissivity` shadows the
default. `CAWorld` and each stock world therefore carry the same 25, the
vanilla world value. A custom world that sets its own keeps it. AEE compensates
at run time through the matcher. The value was 40 before the lighting review,
which restored 25 (see the revision below).

`DayLighting` is re-homed into the chain in the same way.

## Load order

`requiredAddons` names `A3_Data_F_Decade_Loadorder`, not the per-map addons
`A3_Map_Stratis`, `A3_Map_Altis`, `A3_Map_Malden`, `A3_Map_Tanoa` and
`A3_Map_Enoch`. The per-map names tripped the engine warning "requires addon
A3_Map_Tanoa" when the Apex addons were absent, and the run gate treats a
warning as an error. `A3_Data_F_Decade_Loadorder` is present in every supported
build, so the anchor loads without the warning. The engine loads AEE on top of
the base-game data. A competing mod that loads later can still win the class.
The load order decides among competing mods. AEE records this caveat and makes
no claim to the last word.

## Engine ceiling per item

The table states the ceiling for each plan item.

| Item | Behaviour | Engine ceiling |
| --- | --- | --- |
| 1 | Complete `HDRNewPars` | Read at world load. No script command changes it |
| 2 | `starEmissivity` 25 | Read at world load. A world that sets its own shadows the shared value |
| 3 | Star brightness model | Run-time pure kernels. The star render scale is scriptable |
| 4 | `DayLighting` night keyframes | Read at world load. No script command changes it |
| 5 | Rain-scaled film grain | Run-time FilmGrain. The engine couples grain and sharpness |
| 6 | Scene-aware shadow distance | Run-time `setShadowDistance`. The classifier is a heuristic |
| 7 | Weather particles and heat haze | Run-time. AEE reads the weather and writes no weather |
| 8 | FilmGrain colour invariant and laser alpha | Run-time. The engine can desaturate only |
| 9 | Video-option ceiling | Document only. A mod cannot set, force or read a video option |
| 10 | Post-process template reference | Document only. AEE ships no template |

## Revision: lighting reference review

Date: 2026-10-06. AEE reviewed the stars, the `DayLighting` night floor and
`SimulWeather` against Workshop 3587581054, "Highlights - HDR & Lighting Suite
[HLS]", by Tyrr. The mod is a comparison only. AEE copies no value from it.

The review restored `starEmissivity` from 40 to the vanilla 25. The 40 doubled
the vanilla star draw and had no physical source. The review left the
`DayLighting` night floor at vanilla, because AEE's values already match the
vanilla keyframes to within 0.001. The review left `SimulWeather` at vanilla,
because the reference change has no source and is not clearly warranted. The
full review is in `lighting-reference-review.md`.

## Run-time ownership per lever

The engine exposes a small set of run-time levers. The table states the owner.

| Lever | Owner | Note |
| --- | --- | --- |
| `setShadowDistance` | AEE optics | The scene-aware shadow distance item |
| `setGusts` | AEE, gated | On when `weatherOwnership` is on. Default off |
| `setHumidity` | AEE, gated | Same setting and default |
| `overcast` | read only | `compat_realweather` owns the server write |
| `rain` | read only | AEE reads |
| `fog` | read only | AEE reads |
| `wind` | read only | AEE reads |
| `HDRNewPars` | none | No script command exists |
| `starEmissivity` | none | No script command exists |
| `Lighting` | none | No script command exists |
| `DayLighting` | none | No script command exists |
| `Weather` | none | No script command exists |

AEE owns three writes and reads the rest. The gated writes avoid a feedback
loop and keep `compat_realweather` authoritative.

## The world lighting matcher

Static per-map tables are rejected. They do not scale to custom and unknown
maps. A keyed table needs one row per map and fails on a map the author never
saw.

The matcher derives the class from facts AEE already publishes. It reads the
latitude from `EFUNC(core,getWorldLocation)`, the biome from `aee_core_biome`,
the terrain signals from `aee_environmental_terrainSignals` and the engine
weather. It consults no map name and no per-map table. The class comes from the
Koppen group, the water fraction and the mean elevation.

The kernels are `fnc_worldLightingClass` and `fnc_worldLightingProfile`. The
binder `fnc_applyWorldLighting` runs once per environment tick. It publishes
`aee_environmental_worldLighting` and `aee_environmental_worldLightingClass`.
It drives the star render scale, the night factor, the grain scale and the haze
scale.

The biome mapping is SOURCED to Koppen, Peel et al. 2007. The profile numbers
are UNSOURCED aesthetic proxies. A custom or unknown world falls back to the
temperate class.

## Source register summary

The register `workshop-copy-source-register.md` lists one row per item. Each
row holds the value or behaviour, the source mod, the Workshop id, the licence
line and the AEE target file. The sources are Real Lighting and Weather
(2809399991), Fluffys (3704702374 and 3737586377), Star Light (3749362906),
Adaptive Shadows (3792830104), Better Visuals (3351805137), Enhanced Visuals
(880703327), Enhanced Video Settings (1223309664) and Post Process Effects
(656307117). Every row carries the same licence line.

## Superseded follow-up

The research note `human-vision-model.md` carries a section "Follow-up:
base-game lighting gaps (not implemented)". It lists items (a) to (e) as
candidates. This record supersedes that section. Items (a) to (e) are now
implemented or recorded. The same ideas appear in the plan `aee-workshop-copy`
and in the source register.

## Consequences

- Good: AEE carries eleven mod ideas as its own behaviour, for every map. The
  licence risk is low because AEE copies no mod content. The matcher scales to
  an unknown map.
- Cost: the config anchor repeats in six world blocks. This is the engine
  requirement. The matcher adds one classification per environment tick.
- Risk: the config override is global and load-order sensitive. A later mod
  can win the class. The shadow classifier is a heuristic. The night darkness,
  the grain, the HDR bloom and the shadow behaviour need an operator in-game
  look.

## References

- `.omo/plans/aee-workshop-copy.md`, including addenda 1 and 2.
- `docs/wiki/research/workshop-copy-source-register.md`: the per-item register.
- `docs/wiki/research/engine-hdr-and-night-ceiling.md`: the HDR and night
  ceiling, the class chain and the per-lever ownership.
- `docs/wiki/research/video-option-ceiling.md`: item 9.
- `docs/wiki/research/post-process-template-reference.md`: item 10.
- `docs/adr/ADR-014-human-vision-model.md`: the base-grade anchor read.
- `docs/adr/ADR-012-cba-settings-taxonomy.md`: the setting taxonomy.
- `docs/wiki/research/human-vision-model.md`: the superseded follow-up.
- BIKI `CfgVideoOptions`: the engine video-option reference.
