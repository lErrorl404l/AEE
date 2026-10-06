# Engine HDR and Night Ceiling

This note records what AEE can and cannot change in the engine image pipeline.
It states the ceiling so no later claim overstates it.

## The anchor lives in the world class chain

`CfgWorlds` holds the engine image settings. A direct child class, for example
`class CfgWorlds { class HDRNewPars {...}; }`, is an unreferenced sibling and
is inert. The engine reads `HDRNewPars`, `DOFPars`, `Lighting` and the
`DayLighting` keyframes through the world class chain:

`CfgWorlds >> DefaultWorld >> CAWorld >> <World>:CAWorld`

AEE re-homes the anchor into `CAWorld` and into every stock world that
redeclares the class: `Stratis`, `Altis`, `Malden`, `Tanoa` and `Enoch`. Each
block uses the explicit base form `class X: X`, so the engine merges the
values instead of replacing the class. Every block carries the same values.
This is the engine's structural requirement, not per-map tuning, so no value
is keyed by a map name. The `requiredAddons` list names
`A3_Data_F_Decade_Loadorder`, not the per-map addons. The per-map names tripped
the engine warning "requires addon A3_Map_Tanoa" when the Apex addons were
absent, and the run gate treats a warning as an error.

## HDRNewPars and DOFPars

`HDRNewPars` is the engine HDR pipeline: bloom, the tonemap curve, the eye
adaptation gains and the night shift aperture. `DOFPars` places the NVG focal
plane. The engine reads both at world load. A script cannot change either at
run time. No `ppEffect` reaches the same stage.

## starEmissivity

`starEmissivity` scales the engine star draw. The engine core declares
`DefaultLighting` with `access = 3` and `starEmissivity = 0.3`. A re-open
merges and propagates, but a world that sets its own `starEmissivity` shadows
it. `CAWorld` and each stock world's `Lighting` therefore carry the same 25,
the vanilla world value (Altis `starEmissivity` = 25). A custom world that sets
its own keeps it. The review against Workshop 3587581054 restored 25 from an
earlier 40, which doubled the vanilla draw with no source. The review is in
`lighting-reference-review.md`.

## DayLighting

`DayLightingBrightAlmost` and `DayLightingRainy` carry the night-darkness
endpoints. The engine interpolates the world lighting between those endpoints
as the sun and moon move. AEE overrides only `deepNight` and `fullNight`. The
other keyframes keep the base game value.

## The probe reads the resolved world

The P84 probe reads `CfgWorlds >> worldName >> HDRNewPars`, not a direct
`CfgWorlds` child. It proves AEE's values reached the engine's class chain, not
an inert sibling. The probe runs headless and renders nothing.

## No runtime command

No script command changes `HDRNewPars`, `DOFPars`, `starEmissivity`,
`Lighting`, the `DayLighting` keyframes or the `Weather` block. These values
are fixed at world load.

## Per-lever ownership

The free run-time weather levers and their owner:

| Lever | Owner |
|---|---|
| `setGusts` | AEE, when `AEE Environmental > Weather > weatherOwnership` is on (default off) |
| `setHumidity` | AEE, same setting |
| `setShadowDistance` | AEE optics, the scene-aware shadow distance item |
| `overcast` | read only. `compat_realweather` owns the server write |
| `rain` | read only |
| `fog` | read only |
| `wind` | read only |

AEE keeps reading `overcast`, `rain`, `fog` and `wind`. It writes gusts and
humidity only when the operator turns ownership on. This avoids a feedback
loop and keeps `compat_realweather` authoritative. The write is server side
and default off.

## The matcher

The config is load time and world independent. AEE adapts at run time through
`fnc_applyWorldLighting`. It runs once per environment tick. It reads latitude
(`core getWorldLocation`), biome (`aee_core_biome`), terrain signals
(`aee_environmental_terrainSignals`) and engine overcast. It classifies the
world with `fnc_worldLightingClass` and derives four bounded scales with
`fnc_worldLightingProfile`: the night factor, the star render scale, the grain
scale and the haze scale. It publishes the profile as
`aee_environmental_worldLighting` and the class as
`aee_environmental_worldLightingClass`.

The class comes from the Koppen group of the biome, the water fraction and the
mean elevation, never from a map name. A custom or unknown world falls back to
the temperate class. The class table is keyed by climate class, not by map.
The biome mapping is SOURCED (Koppen, Peel et al. 2007). The profile numbers
are UNSOURCED aesthetic proxies.

## Honest ceiling

AEE proves the resolved config values headless. AEE cannot prove the rendered
frame headless. A script cannot set a video option or read the operator's
choice. The HDR bloom, the night darkness, the grain and the shadow behaviour
each need an in-game look. This note claims no more.
