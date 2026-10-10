# Thermal / material control capability matrix (issue #127)

This is the single reference for what the Arma 3 engine exposes to
thermal-imaging control, what AEE drives, and what is proven in-game.
It is the formal record of the #204 investigation and the #127 capability
matrix - written so the engine-ceiling knowledge is not re-learned the
hard way.

## How to read this

- **Lever**: the engine command or config surface.
- **Baked (texture / PBO)**: a texture or a material the engine reads at
  load. A script cannot change it at run time.
- **Dynamic (scripted)**: a command AEE calls at run time.
- **Ceiling**: a real limit. Where a property is unreadable or unbakeable,
  the row records the ceiling. It never guesses a value.
- **Reaches TI?**: does it change what the thermal image shows?
- **AEE status**: NOT BUILT (documented, not implemented), IMPLEMENTED
  (wired, off-game tested), IN-GAME PROVEN (seen working by the user).
- **Proof**: the in-game observation or the mechanism.

## The per-surface and per-object-type matrix (baked vs dynamic)

This is the matrix the issue asks for. Each row names the thermal and
material properties of one surface or object type, and states which are
baked and which are dynamic. A row with no dynamic entry is a ceiling.
Every row names its source.

| Target | Baked (texture / PBO) | Dynamic (scripted) | Ceiling | Source |
|---|---|---|---|---|
| **Terrain surface** | Satellite texture `s_satout_co.paa` and the WRP layer rvmats (for example `s_00.rvmat`). The GDT surface mask is baked in the WRP. | The second sun term only (`fnc_applySecondSun`, brightness `radiation * 13`). | No runtime terrain material swap command exists. Per-pixel temperature is impossible. A PBO path override changes the baked baseline at load, never at run time. | Issue #128 layer 2. AEE `fnc_applySecondSun.sqf`. A3TI `DEFAULT_SECONDSUN_BRIGHTNESS 13`. |
| **Static rocks and map props** | The model's own `StageTI` texture. Objects with none fall back to `default_TI.rvmat`, whose `StageTI` points at `a3\data_f\default_ti_ca.paa`. | The second sun term. `setObjectMaterial` and `setObjectTexture` reach them only when the model ships `hiddenSelections`. WRP-baked objects are enumerable with `nearestTerrainObjects`. | A model with no `hiddenSelections` takes the sun term and the load-time config caps only. | `default_TI.rvmat` (StageTI). The acemod command database, entries `setObjectMaterial`, `setObjectTexture`. Issue #128 layer 1 bonus. |
| **Buildings with `hiddenSelections`** | The model's `StageTI` texture, per material. | `setObjectMaterial` per selection (`fnc_applyBuildingThermal` calls `fnc_applySelectionThermal`), and `setObjectTexture` per selection with the FLIR procedural colour. | Per selection only. Never per pixel. Glass stays model-baked. | AEE `fnc_applyBuildingThermal.sqf`, `fnc_applySelectionThermal.sqf`. The acemod command database, entry `setObjectMaterial`. |
| **Buildings without `hiddenSelections` (map-embedded)** | The `StageTI` texture and the engine fallback. The render heat caps `afMax` and `mfMax` on the `All` root reach them. | The second sun term only. | No `hiddenSelections` means no per-selection swap. The caps are load-time config, not a runtime control. | AEE `addons/thermal/config.cpp` (the `All` root caps). Issue #204. |
| **Vehicles** | Per-material `StageTI` textures. The render heat keys `htMin`, `htMax`, `afMax`, `mfMax`, `mFact`, `tBody`. | FULL. `setVehicleTIPars [engine, wheels, weapon]` from `fnc_applyEngineThermal`. `setObjectTexture` per selection. `setObjectMaterial` per selection. Damage-state heat. | Three native heat slots only. Beyond them, per-selection swaps. Glass reflections are model-baked. Per-pixel temperature is impossible. | AEE `fnc_applyEngineThermal.sqf`, `fnc_applySelectionThermal.sqf`. The acemod command database, entry `setVehicleTIPars`. Issue #128 layer 3. |
| **Infantry body** | The engine renders the body natively from the render heat model. ACE3 sets `Man` `mFact = 1`, `tBody = 32`. AEE sets the same. | `setObjectTexture` per clothing selection (`fnc_applyClothingThermal`). | The base body renders natively. Only the worn selections are swappable. `setVehicleTIPars` does not work on infantry weapons. | The `ace_thermals` config. AEE `addons/thermal/config.cpp`. The acemod command database, entry `setVehicleTIPars`. |
| **Infantry clothing and gear** | The garment's own TI texture. A ghillie suit references a cold TI map, so it hides the wearer. | `setObjectTexture` per selection. The solar absorptance is read from the worn texture. | Only the selections the model ships. | AEE `fnc_applyClothingThermal.sqf`. |
| **Infantry weapons** | The weapon TI texture. Its alpha channel is barrel heat. | `setObjectTexture` on the weapon selections (`fnc_applyWeaponBarrelHeat`). | `setVehicleTIPars` does not work on infantry weapons. | The BIKI "Thermal Imaging Maps" page (oldid 155895). AEE `fnc_applyWeaponBarrelHeat.sqf`. The acemod command database, entry `setVehicleTIPars`. |
| **Vegetation** | Engine-baked `StageTI`. | The second sun term only. | No per-object command exists. | Issue #204. The thermal dossier section 2.5. |
| **Glass** | The `StageTI` texture (cold), for example `default_glass_ti_ca.paa`. The `NoTiWrite` render flag excludes a face from the thermal buffer. | `setObjectMaterial` per selection, when the model ships `hiddenSelections`. | The glass TI reflection is model-baked. | `default_noTIwrite.rvmat`. Issue #128 layer 3. |
| **Optics and the display window** | The engine thermal palette (`setPiPEffect` mode 2, `setCamUseTI` modes 0 to 7) and the native render pass. | `setTIParameter ["OutputRangeStart"/"OutputRangeWidth", v]` (`fnc_applyEngineThermal`). A PIP render target with `setPiPEffect [3]` is NOT BUILT. | The window can only compress and offset. It cannot stretch. The palette is engine-fixed. | The acemod command database, entries `setTIParameter`, `getTIParameters`, `setPiPEffect`, `setCamUseTI`. |
| **The native render pass** | The compiled thermal renderer. | None. `ppEffect`s do not apply in vision mode 2. The fusion track runs on the NVG channel instead. | No custom renderer. The thermal pass is not interceptable. | The thermal dossier section 3. Issue #204. |

### Unreadable properties (the read-back ceilings)

Some properties have no read-back at all. They are ceilings, not gaps.

- `getObjectMaterials` returns only the `setObjectMaterial` overrides. It
  does not return a model's default materials. The baked material of an
  object is therefore unreadable. Source: AEE `fnc_getObjectMaterial.sqf`.
- `getTIParameters` reads the display window. There is no read-back of the
  engine's internal `thermalValue`. Source: the acemod command database,
  entry `getTIParameters`.
- The engine does not expose a vehicle's engine mass or wetted area. AEE
  uses the whole-vehicle mass and bounding box as a stated assumption.
  Source: AEE `fnc_calculateVehicleHeat.sqf`.

## The levers (verified against Bohemia reference + workshop prior art)

| Lever | What it controls | Reaches TI? | AEE status | Proof |
|---|---|---|---|---|
| `setTIParameter ["OutputRangeStart"/"OutputRangeWidth", v]` | Display window over the raw thermal signal (AGC: compress/offset) | Yes - reshape output curve | IMPLEMENTED (fnc_applyEngineThermal) | In-game: correct contrast read, WHOT/BHOT polarity works |
| `vehicle setVehicleTIPars [engine, wheels, weapon]` | Per-vehicle heat, each 0..1, independent of part usage | Yes - per-component heat | IMPLEMENTED (driven from AEE per-selection physics) | In-game: vehicles warm up/cool via the physics model |
| Second sun (`#lightpoint` + `setLightDayLight true`) | The engine's sun-heat term, added to every object | Yes - global heat bias | IMPLEMENTED (fnc_applySecondSun) | In-game: vehicles DARKENED with second sun OFF (the #204 isolation test) |
| `setObjectMaterial [sel, rvmat]` | Per-selection material swap | Yes - ONLY if model ships hiddenSelections; coefficient layer | IMPLEMENTED (applyBuildingThermal, applySelectionThermal) | In-game: FPN material renders on objects per-selection |
| `setObjectTexture [sel, tex]` | Per-selection texture paint | Yes - Stage1 texture is what the TI pass reads for objects | IMPLEMENTED (32-level heat paint, MKK mechanism) | In-game: heat-colour paint reads on vehicles/weapons |
| `stage setCamUseTI mode` | Baked palette LUT (0-7) for a camera | Yes - palette only, not data | NOT BUILT (vanilla pipeline uses it natively) | BI reference |
| `"rt" setPiPEffect [3, ...]` | Render-to-texture with FULL custom colour-correction | Yes - the PIP track (#204 Track A) | NOT BUILT (fusion uses ppEffectForceInNVG instead) | Dossier section 4.2 |
| `disableTIEquipment` | Kill TI capability | Yes - on/off | NOT BUILT | BI reference |
| `getTIParameters` / `getVehicleTIPars` | Read-back | - | NOT USED (state tracked in AEE variables) | - |
| Render heat keys `htMin`, `htMax`, `afMax`, `mfMax`, `mFact`, `tBody` | Per-object simulated temperature model (the StageTI channel coefficients) | Yes - object heat | IMPLEMENTED (load-time config in the single `CfgVehicles` block) | BIKI "Thermal Imaging Maps" oldid 155895; P91 config probe |
| AI IR keys `irTarget`, `irTargetSize`, `irScanRangeMin`, `irScanRangeMax`, `irScanToEyeFactor`, `irScanGround` | AI infrared detection model | No - separate from the rendered image | IMPLEMENTED (load-time config) | Vanilla samples in the base config |
| Per-optic `thermalMode[]`, `thermalNoise[]`, `thermalResolution[]` | Optic thermal palette, noise and resolution | Yes - optic thermal keys | IMPLEMENTED (generated `CfgWeapons` block) | Vanilla `optic_tws` mode `TWS`, `ItemInfo >> OpticsModes` |
| `#lightreflector` with `setLightIR true` | Active-IR illuminator | Yes - an IR optic sees it, the eye does not | IMPLEMENTED (`fnc_startActiveIR`, setting-gated) | Mechanism UNSOURCED; workshop idea re-implemented |
| `BettIR_Config` class | Declares AEE thermal optics compatible with BettIR | - | IMPLEMENTED (interop declaration) | Interop contract |
| `visionMode[]` and `thermalMode[]` probe | Runtime native-thermal capability read | - | IMPLEMENTED (`fnc_probeThermalCapability`, pure) | Pure kernel, source-contract tested |

## The baked / immutable layers (the engine ceiling)

These cannot be changed at runtime by any script. They are the walls
the #204 investigation hit and proved.

| Layer | Why it is baked | Proof |
|---|---|---|
| Terrain surface texture | No runtime terrain-material swap exists; satellite `s_satout_co.paa` is a baked image | #204: all maps verified identical structure |
| Terrain/vegetation/rock heat | Only the second-sun term reaches them; no per-pixel control | #204: all vanilla flat decals report `tex=[] mats=[]` |
| Object-decal heat on terrain | Decals render as terrain projections the TI pass ignores | #204: Land_DirtPatch + drop billboards invisible in TI |
| The native TI renderer itself | Compiled, non-interceptable; ppEffects do not apply during vision mode 2 | #204: RPT showed handles created, never applied |
| Gen-1/2 weapon heat | `setVehicleTIPars` does not work on infantry weapons | Dossier section 2.3 |
| Infantry base body | Renders natively at a fixed ~33 C skin temperature | Dossier section 2.5 |

## The engine's own temperature model (the baked baseline)

The engine renders thermal from its own per-model temperature model. The
keys are `htMin` and `htMax` (half-cooling time in seconds), `afMax` and
`mfMax` (capped surface temperature when active and when moving), `mFact`
(metabolism influence) and `tBody` (metabolism surface temperature). A
time-integrated model needs these keys. A texture blit would need none of
them.

The vanilla values, read from the shipped configs:

| Class | htMin | htMax | afMax | mfMax | mFact | tBody |
|---|---|---|---|---|---|---|
| `AllVehicles` (data_f) | 60 | 1800 | 200 | 100 | 0.2 | 150 |
| Tank (armor_f) | 60 | 1800 | 100 | 80 | 1 | 250 |
| Boat (boat_f) | - | - | 100 | 80 | 1 | 150 |
| Animal (animals_f) | - | - | 30 | 0 | 1 | 37 |
| `Man` / `AllVehicles` (ACE3 `ace_thermals`) | 60 | 1800 | 70 | 50 | 0 / 1 | 0 / 32 |

The `StageTI` texture is per material and engine-baked. AEE ships no
texture and cannot repaint an arbitrary object. A surface needs a
`class StageTI { texture = ... }` to render in the engine TI mode. The
engine's own `data_f\default_TI.rvmat` points `StageTI` at
`a3\data_f\default_ti_ca.paa`.

## The AEE architecture that works (from #204, in-game proven)

The PP-effect gate on vision mode 2 forced the two-track answer:

1. **Track B - fusion (BUILT, IN-GAME PROVEN)**: run NVG (moddable
   pipeline), composite an emissive thermal overlay from AEE physics on
   top.  Full post-process freedom via `ppEffectForceInNVG`.
2. **Track A - PIP (NOT BUILT, documented)**: render-to-texture via
   `setPiPEffect [3]` for scopes/sights - the SkeetIR pattern.

The physics-driven lever set that reaches the TI image:
`setVehicleTIPars` + second sun + `setTIParameter` window.  These are
what make the ENTIRE physics pipeline (per-selection temps, exhaust,
impact heat) visible to the thermal camera.

## Priority for future work

1. **Track A (PIP)** - the only path to custom scopes/sights thermal
2. Custom proxy-plane model - the only path to terrain heat visuals
3. `getTIParameters` read-back - if we need the engine's actual window

## Source

- Dossier: `thermal-nvg-architecture-dossier.md` (sections 2.3, 2.5, 4)
- Workshop audit: `engine-thermal-mechanisms.md` (the proven mods)
- Command database: the acemod/arma3-wiki command DB v2.22, entries
  `setVehicleTIPars`, `setTIParameter`, `getTIParameters`,
  `setObjectMaterial`, `setObjectTexture`, `setPiPEffect`, `setCamUseTI`
- Vanilla configs: `data_f` (`AllVehicles`), `armor_f` (Tank), `boat_f`,
  `animals_f`, and `default_TI.rvmat`
- ACE3: the `ace_thermals` config (v3.21)
- A3TI: `constants.h` (`DEFAULT_SECONDSUN_BRIGHTNESS 13`),
  `fn_createSecondSun.sqf`, `fn_getThermalSelections.sqf`
- BIKI: "Thermal Imaging Maps" (oldid 155895) for the channel semantics
- In-game tests: the #204 RPT trail
- Issue #128: the three control layers (PBO path override, terrain layer
  override, anchor-based per-component control)
