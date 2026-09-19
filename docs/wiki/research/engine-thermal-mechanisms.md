# Engine thermal-imaging mechanisms — workshop mod audit (issue #204)

Five workshop thermal mods studied in depth (unpacked from the local
workshop PBOs):

| Workshop ID | Mod | Mechanism |
|---|---|---|
| 2041057379 | A3 Thermal Improvement (A3TI, original) | ppEffects over DTV channel + object texture swaps + second sun |
| 3725008325 | A3TI FUSION NVG Thermal (alpha) | Same as A3TI, adds thermal-NVG fusion detection |
| 3753145363 | MKK Thermal Improvement | Full replacement pipeline: disableTIEquipment + ppEffects + per-object heat model |
| 2494550406 | HMCS thermal edited | StageTI rvmats pointing at `default_hot_ti_ca.paa` |
| 3759527903 | FPANO ECOTI | HUD overlay only (not thermal imaging) |

## The definitive mechanism: StageTI texture = the thermal image

Every mod that renders thermal content into the engine's TI mode does
the SAME thing: **point the rvmat's `class StageTI` at a texture, and
the engine renders that texture as the object's thermal appearance.**

The engine's own `data_f\default_TI.rvmat`:

```
ambient[] = {1,1,1,1};
diffuse[] = {1,1,1,1};
emmisive[] = {0,0,0,1};
class StageTI {
    texture = "a3\data_f\default_ti_ca.paa";
};
```

Decoded engine TI textures (flat colours — NOT coefficient masks):

| Texture | RGBA mean | Appearance |
|---|---|---|
| `default_ti_ca.paa` | R=255 G=0 B=0 A=0 | pure red (hot) |
| `default_vehicle_ti_ca.paa` | R=145 G=46 B=0 A=0 | orange (warm) |
| `default_glass_ti_ca.paa` | R=0 G=0 B=0 A=0 | black (cold) |
| character `*_ti_ca.paa` | R=255 G=0 B=0, A varies | red with alpha = heat map |
| HMCS `hm_burner.rvmat` | StageTI = `default_hot_ti_ca.paa` | renders hot |

**Our earlier conclusion that "StageTI is a heat-receptiveness
COEFFICIENT mask (R=sun/G=engine/B=friction/A=metabolism)" was
WRONG.** The BIKI "Thermal Imaging Maps" page describes the colour
channels of the TI TEXTURES (what the model painter encodes), not a
runtime heat model.  The engine renders the StageTI texture directly.

**The alpha channel is the heat map**: characters use R=255 fixed red
with alpha varying per region (face high alpha = hot, clothing lower).
The TI pass blends the texture RGB by its alpha into the TI image.

## Why vanilla TI looks "orange"

The default TI texture is red (255,0,0), the vehicle texture is orange
(145,46,0).  A vanilla scene in TI shows objects tinted red/orange by
their StageTI textures, cold surfaces (glass, metal without TI stages)
dark.  This matches the user report: "default thermals is orange".

## How the proven mods build thermal WITHOUT the engine's TI channel

**A3TI** (the pattern MKK copied):
- Runs the camera in the **DTV (normal) channel** for WHOT/BHOT, NOT
  engine TI mode.  `case 0/1` require `currentVisionMode == DTV`.
- Paints every object's thermal selections with
  `#(rgb,8,8,3)color(1,0.1,0.2,1)` (red) via `setObjectTexture`, and
  `setObjectMaterial` to a rvmat with an `EmissiveWhite` material.
- Adds a **second sun** lightpoint: `setLightDayLight true`,
  brightness **13** (TI) or **0.8** (fusion), attenuation
  `[10e10, 150, 4.3e-5, 4.3e-5]`, ambient `[0.5,0.5,0.5]`.
- Layers ppEffects over the DTV image: ChromAberration(200),
  DynamicBlur(500), FilmGrain(2000), ColorCorrections(2500).
- **BHOT = WHOT + `ColorInversion` ppEffect at 2501** (engine effect
  type, not a `1-b` pixel flip).
- Fusion (WHOT/BHOT over NVG) requires `currentVisionMode == NVG` and
  sets `ppEffectForceInNVG true` on EVERY effect.  Uses the
  `EmissiveWhite.rvmat` (emissive white) material swap so objects glow
  white against the NVG scene.

**MKK** (the modern refinement):
- Detects the optics config (`getAvailableModes` scans
  `OpticsIn >> visionMode` for "normal"/"nvg"/"ti").
- **`disableTIEquipment true` on the vehicle** — kills the vanilla TI
  channel, then draws its own thermal over DTV via ppEffects.
- Per-object highlight system (`setThermalMaterials`, 513 lines):
  heat state per vehicle (engine/motion/cooldown, tau 120 s warmup,
  320 s cooldown), quantised to 32 levels, applied as procedural
  textures `#(rgb,8,8,3)color(r,g,b,1)` per thermal selection.
- Priority ladder (script_constants.hpp):
  ChromAberration 205, WetDistortion 305, DynamicBlur 505,
  FilmGrain 2005, ColorCorrections 2505, ColorInversion 2510,
  Spectrum 2515, Resolution 3000.
- `getTIParameters`/`setTIParameter ["MaxResolution", ...]` — drives
  the ENGINE TI sensor resolution per-FOV (pixelation).
- `refreshThermalSensor` PFH: re-applies FilmGrain intensity with a
  random jitter every `refreshRate` (0.01-5 s) — the "sensor update"
  flicker.
- BHOT uses `ColorInversion` at 2510, exactly like A3TI.
- Brightness/contrast presets default `[1.16, 0.62, 0, 0]` — the
  SAME values A3TI uses (DEFAULT_TIPP_SETTINGS).

## ppEffect priority map (the proven, non-colliding ladder)

A3TI / MKK priorities (both work in-game):

| Priority | Effect | Purpose |
|---|---|---|
| 200/205 | ChromAberration | lens dispersion |
| 305 | WetDistortion | rain on lens |
| 400/500/505 | DynamicBlur | defocus |
| 1000 | RadialBlur | vignette (A3TI uses for DTV edge) |
| 1500/2000/2005 | FilmGrain | sensor noise |
| 2500/2505 | ColorCorrections | thermal tint / brightness |
| 2501/2510 | ColorInversion | BHOT polarity |
| 2515 | ColorCorrections (2nd) | spectrum grade |
| 3000 | Resolution | TI pixelation |

Our mod's ladder (optics 3000/4000/5000, NVG 1200-6000, thermal
1300-5200) does NOT collide internally, but the "5100 already exists"
error means a thermal handle at 5100 collided with the NVG CC at 5100
when both modules were live.  The proven mods keep everything under
3000 except the resolution effect.

## Second sun — the proven parameters

A3TI second sun (TI):
```
setLightBrightness 13;
setLightDayLight true;
setLightAttenuation [10e10, 150, 4.3e-5, 4.3e-5];
setLightAmbient [0.5, 0.5, 0.5];
```
Diet sun (fusion): brightness 0.8, `setLightDayLight false`.

The attenuation `[a,b,c,d]`: a = constant (10e10, effectively none),
b = linear (150), c/d = quadratic (4.3e-5).  The linear term of 150
means the light falls off over ~150 m.  Our `* 6` cap was arbitrary;
A3TI uses a FIXED 13 and does not modulate it by physics radiation —
the second sun is a constant "sensor illumination boost", present
whenever TI is active, day OR night.

## What this means for AEE

1. **The band-rvmat approach (grey diffuse, no StageTI) is wrong.**
   The proven mechanism is a StageTI texture (or object texture swap
   with the DTV channel + ppEffects).  A surface needs a
   `class StageTI { texture = ... }` to render in the engine's TI
   mode; a material with no StageTI and a grey diffuse does not
   render thermal at all (our "everything white" was the diffuse
   fallback, and "nothing applied" was the missing StageTI).

2. **Thermal should be drawn over the DTV channel** (A3TI/MKK), with
   the engine's TI disabled (`disableTIEquipment`), OR the objects
   get StageTI textures that carry the physics heat as alpha.

3. **BHOT is `ColorInversion` ppEffect**, not a `1-b` brightness flip.

4. **The second sun is a fixed boost (13), not physics-modulated**,
   with `setLightDayLight true` and the linear 150 attenuation.

5. **`ppEffectForceInNVG true`** is the fusion mechanism — effects
   apply over the NVG channel (mode 1), which is how ENVG-style
   fusion renders.

6. The engine TI texture alpha is the heat map — to paint a surface
   at a given heat, use a procedural texture with the desired RGB
   and alpha, e.g. `#(argb,8,8,3)color(r,g,b,alpha,TI)` or point the
   StageTI at a custom *_ti_ca.paa.

## Deeper: TI texture gradient semantics (HMCS decode)

A custom part TI texture (HMCS `hm_02_ti_ca.paa`, decoded): a red
gradient, R=255 constant, G varies 8-40, B=0, A=0.  The G channel is
the temperature variation across the surface — purer red (low G) is
hotter, higher G trends to yellow-orange (cooler).  So:

- a solid swatch (default_ti = 255,0,0) = uniform hot
- a red-with-G-gradient = thermal variation across the part
- a red-with-varying-alpha texture (characters) = heat map via alpha
- black (default_glass_ti = 0,0,0) = cold/transparent

The TI pass renders the StageTI texture's RGB directly, modulated by
alpha.  This is the complete engine thermal-texture model.

## Deeper: the fusion material (A3TI EmissiveWhite.rvmat)

```
ambient[] = {20,20,20,1};        // 20x ambient
diffuse[] = {0.005,0,0,0};       // near-black diffuse
emmisive[] = {500,500,500,500};  // 500x emissive
renderFlags[] = {"AlwaysInShadow"};
class Stage1 { texture = "A3TI\DATA\TI_white.paa"; };  // solid white 16x16
```

Objects swapped to this material glow pure white (TI_white.paa =
255,255,255,255) independent of scene lighting via the 500 emissive
and AlwaysInShadow.  This is the fusion-NVG hot-object look.  AEE's
earlier "soldier flashed white" observation was this exact mechanism.

## Deeper: thermal spectra are ColourCorrections matrices (MKK)

Each thermal palette (WHOT, BHOT, GREENHOT, REDHOT, SEPIA, ARCTIC,
RAINBOW/THERMAL, IRONBOW, AMBERHOT, WHOTREDCOLD) is a
`ColorCorrections` ppEffect matrix:

```
ppEffectAdjust [brightness, contrast, offset,
    [R_black, G_black, B_black, A_black],   // black-point
    [R_white, G_white, B_white, A_white],   // white-point
    [R_tint,  G_tint,  B_tint,  A_tint]]    // colour tint
```

Example WHOTREDCOLD: `[1,1,0, [0.08,0.01,0,0.08], [1.32,0.54,0.40,0.52], [0.70,0.22,0.10,0.28]]`.
BHOT = WHOT + `ColorInversion` ppEffect (priority 2510), applied on top.

## Deeper: thermal selection discovery (A3TI/MKK)

1. Man: ALL getObjectTextures indices (uniforms have no
   hiddenSelections).
2. Vehicle config `MKK_TI >> mkk_ti_thermal_improvement_thermalSelections`
   or legacy `A3TI_ThermalSelections` (indices or names) — explicit.
3. `textureSources >> textures` non-empty slots.
4. Fallback: all hiddenSelections EXCEPT names containing "mfd".

Cached per class in missionNamespace.  AEE should use the same chain:
explicit per-class override first, then textureSources, then all-but-MFD.

## Deeper: config-driven mode detection (A3TI getAvailVisions)

The engine exposes an optic's thermal modes in config:
`CfgVehicles >> vehicle >> Turrets >> X >> OpticsIn >> Y >> visionMode`
values "normal"/"nvg"/"ti", and `thermalMode[]` (0=WHOT, 1=BHOT,
2=green-hot, 3=green-cold, 4=red-hot, 5=red-cold, 6=white-hot-red-cold,
7=shade-of-red-green).  A3TI reads `thermalMode` and `mod 2` to map to
WHOT/BHOT.  This is how a mod knows which modes an optic supports
without hardcoding classnames.

## Deeper: the dispatch (how proven mods hook the N key)

A3TI: `["KeyDown"]` on display 46 + CBA keybinds (B = next mode,
shift-B = previous).  The KeyDown handler sleeps 50 ms (waits for the
engine's own vision cycle), compares `currentVisionMode` to the stored
value, and calls `cycleVision` when it changed — which re-runs
`ppEffects` to rebuild the effect stack.  A cameraView/turret/unit
player-EH also triggers the rebuild.  The effect stack is destroyed and
recreated on every mode/view/vehicle change (cleanup + rebuild), not
adjusted in place.

MKK: `addUserActionEventHandler ["nightVision", "Activate", ...]` on
the vanilla nightVision action + `addPlayerEventHandler` on
unit/cameraView/turret, plus a 0.25 s maintenance PFH that compares the
context array (platform, optics, vision-state, special, configured) and
only rebuilds when it changed.

## Deeper: aperture (night sensor)

Both mods: `setAperture -1` during the day (sunOrMoon==1) or out of
gunner, `setAperture 15` at night in thermal, cycling through
[-1, 15, 25].  Aperture is the camera exposure boost — essential for
night thermal to be visible.  AEE does not drive aperture at all.

## Deeper: the second sun attenuation

`setLightAttenuation [10e10, 150, 4.3e-5, 4.3e-5]` — constant 10e10
(no constant falloff), LINEAR 150 (falls off over ~150 m), quadratic
4.3e-5.  The light is attached at the camera position.  `setLightDayLight
true` for TI (brightness 13), `false` for fusion (brightness 0.8).

## Deeper: fusion-mode gating (A3TI filterVisions)

Fusion modes are ONLY offered when ALL of: the optic's config has a
thermal mode (config `thermalMode[]` non-empty), AND the current vanilla
vision mode is NVG (1).  In DTV (0), only the thermal modes are offered.
This is the ENVG-B behaviour model: a thermal-capable NVG shows fusion
over the NVG channel; a scope shows thermal over DTV.

The fusion branch requires `currentVisionMode == NVG` (1) and every
ppEffect gets `ppEffectForceInNVG true` — the effect applies ONLY to
the NVG-rendered frame, leaving the normal frame untouched.  The DTV
branch requires `currentVisionMode == DTV` (0) and the effects apply to
the normal frame (no ForceInNVG).

This means: a mod CANNOT put thermal on the engine's TI channel (mode
2) and also run its own WHOT/BHOT — the proven mods disable the native
TI (`disableTIEquipment true`) and use DTV or NVG as the base channel.
The engine TI mode (2) itself is left for vanilla.

## Deeper: the aperture (exposure) rule

Both mods drive `setAperture`:
- day (sunOrMoon == 1) or not in gunner / not active → `setAperture -1`
  (auto)
- night in thermal → `setAperture 15` (preset), cycling [-1, 15, 25]
  via a keybind

Without this, night thermal is under-exposed (the camera auto-exposure
is tuned for daylight).  AEE drives no aperture — a gap.

## Deeper: per-class profile discovery (MKK getModuleThermalProfile)

A mission module (CfgVehicles class, Eden-placed) carries the thermal
profile: generation (1-3), palette name (WHOT_BHOT, GREENHOT_GREENCOLD,
WHOTREDCOLD, REDHOT_REDCOLD, IRONBOW, AMBERHOT, SEPIA, ARCTIC,
THERMAL).  The profile's spectrum overrides (brightness, contrast,
offset, alpha, colourize RGBA, highlight brightness) become the
ColorCorrections + grain + blur + refresh-rate settings for that optic.
Per-vehicle config profiles (class MKK_TI in the vehicle's CfgVehicles)
provide the same overrides per vehicle class.  The active profile is
selected by the player's current optics/vehicle, not globally.