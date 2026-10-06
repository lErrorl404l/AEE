# Video Option Ceiling

This note records the `CfgVideoOptions` ceiling. It states what a mod can add
or raise, and the hard limit that no mod can pass. Item 9 of the
`aee-workshop-copy` plan records it. AEE adds no `CfgVideoOptions` block and
changes no video option.

## What a mod can add or raise

`CfgVideoOptions` holds one class for each video option. A quality tier is a
child class of that option. A mod can add a tier and can widen the range. The
engine shows the new tier in the options menu. The engine stores the operator
choice in the operator profile.

The Enhanced Video Settings mod (Workshop 1223309664) widens these ranges in
`GF_enhancedVideo/config.cpp`. The table quotes that file.

| Option class | Field | Range |
| --- | --- | --- |
| `Visibility` | `minValue` to `maxValue` | 5 to 40000 |
| `ObjectsVisibility` | `minValue` to `maxValue` | 5 to 30000 |
| `ShadowsVisibility` | `minValue` to `maxValue` | 5 to 3000 |
| `PPSharpen` | `minValue` to `maxValue` | 0 to 4 |
| `PPBloom` | `minValue` to `maxValue` | 0 to 3 |
| `PPContrast` | `minValue` to `maxValue` | 0 to 2 |
| `PPSaturation` | `minValue` to `maxValue` | 0 to 2 |
| `PPDOF` | `minValue` to `maxValue` | 0 to 5 |
| `PPBrightness` | `minValue` to `maxValue` | 0 to 2 |
| `PPRotBlur` | `minValue` to `maxValue` | 0 to 2 |
| `PPRadialBlur` | `minValue` to `maxValue` | 0 to 2 |

The `OverallSettings` block binds the menu names to the classes. The names
`visibility`, `objectVisibility` and `shadowVisibility` bind to the three
visibility classes above.

The mod also adds whole quality tiers. The next table lists the tiers that
carry a value.

| Option class | Added tier | Field | Value |
| --- | --- | --- | --- |
| `TerrainQuality` | `Verylowlow` | `terrainGrid` | 100 |
| `TerrainQuality` | `VeryHigh2` | `terrainGrid` | 2.6 |
| `ShadowQuality` | `VeryHigh2` | `shadowType` | 2 |
| `ShadowQuality` | `VeryHigh2` | `textureSize` | 4096 |
| `ShadowQuality` | `VeryHigh2` | `shaderQuality` | 3 |
| `ShadowQuality` | `VeryHigh2` | `cascadeLayers` | 8 |
| `Particles` | `High` | `particlesSoftLimit` | 16000 |
| `Particles` | `High` | `particlesHardLimit` | 18000 |
| `DynamicLights` | `Extreme` | `value` | 32 |
| `CloudQuality` | `Extreme` | `value` | 256 |
| `PiP` | `VeryHigh2` | `value` | 4000 |

`TerrainQuality` is a grid. A smaller `terrainGrid` value gives a finer mesh.
The mod adds a coarse tier at 100 and a fine tier at 2.6. `ShadowQuality`
selects the shadow map. The mod adds a tier with eight cascade layers.

## The hard ceiling

A mod cannot set a video option. The engine reads the operator choice at
start. The class declares the allowed range and the menu tier only.

A mod cannot force a value. The engine writes the profile, not the mod. A mod
that ships a config entry sets a default for a fresh profile only.

A mod cannot read the operator choice. No script command returns the current
`CfgVideoOptions` values. `getResolution` returns the screen size. It returns
no quality tier.

The Enhanced Video Settings mod adds a checkbox that calls `setTerrainGrid`. A
script command can override the terrain grid for one session. That command is
a run-time lever. It does not change the stored video option. The command
`setTerrainGrid -1` restores the video option.

## AEE position

AEE adds no `CfgVideoOptions` block. AEE documents the levers in this note and
leaves the choice to the operator. A video-option change needs the operator
menu. ADR-010 states the same limit for scene sharpening.

## Sources

- Enhanced Video Settings, Workshop 1223309664, `GF_enhancedVideo/config.cpp`:
  the ranges, the added tiers and the option classes.
- BIKI `CfgVideoOptions`: the engine reference for the option classes.
- ADR-010: the scriptable post-process set and the sharpening limit.
- `engine-hdr-and-night-ceiling.md`: the HDR and night ceiling.
- Item 9 of `.omo/plans/aee-workshop-copy.md`.

The BIKI page returned HTTP 403 in this session. This note does not restate
the engine base values. The ranges above come from the mod config. That file
is a primary source unpacked from the mod PBO.
