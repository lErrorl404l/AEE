# Engine HDR and Night Ceiling

This note records what AEE can and cannot change in the engine image pipeline.
It states the ceiling so no later claim overstates it.

## HDRNewPars

`CfgWorlds >> HDRNewPars` is the engine HDR pipeline. The engine reads the
block at world load. It sets bloom, the tonemap curve, the eye-adaptation
gains and the night-shift aperture. A script cannot change the block at run
time. No `ppEffect` reaches the same stage. AEE ships the block in
`addons/environmental/config.cpp`, so the values apply from the first frame.

## Load order

Every mod that ships `CfgWorlds >> HDRNewPars` competes for the same block.
The last addon to load wins on a conflicting key. AEE cannot control the load
order of another mod. AEE also cannot detect a later override at run time,
because the engine does not publish the winning values. The probe P84 reads
the loaded values in the test rig only.

## starEmissivity

`starEmissivity` scales the engine star draw. The engine reads the value from
the world's own `Lighting` class. The base config only forward-declares
`DefaultLighting`, so AEE overrides each official world's `Lighting`. The
value is 40, mid-band between Fluffys (30) and Real Lighting and Weather
(60). A higher value raises the star brightness. A custom world keeps its own
value. The engine still draws its own star field. AEE does not ship a star
texture.

## DayLighting

`CfgWorlds >> DayLightingBrightAlmost` and `DayLightingRainy` carry the
night-darkness endpoints. The engine interpolates the world lighting between
those endpoints as the sun and moon move. AEE overrides only `deepNight` and
`fullNight`. The other keyframes keep the base game value.

## Interaction risk

The eye-adaptation gains (`eyeAdaptFactorLight`, `eyeAdaptFactorDark`) and the
night-shift aperture meet AEE's own eye model and NVG gain. A dark `fullNight`
endpoint lowers the scene luminance. The AEE eye model then raises its
adaptation. The NVG gain raises the tube brightness next. The two effects can
compound. The P84 probe proves the config values, not the composed image. The
composed image needs an operator look in the game.

## Honest ceiling

AEE proves the config values headless. AEE cannot prove the rendered frame
headless. A script cannot set a video option or read the operator's choice.
The HDR bloom, the night darkness, the grain and the shadow behaviour each
need an in-game look. This note claims no more.
