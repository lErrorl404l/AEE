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