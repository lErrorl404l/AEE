# Thermal / material control capability matrix (issue #127)

This is the single reference for what the Arma 3 engine exposes to
thermal-imaging control, what AEE drives, and what is proven in-game.
It is the formal record of the #204 investigation - written so the
engine-ceiling knowledge is not re-learned the hard way.

## How to read this

- **Lever**: the engine command or config surface.
- **Reaches TI?**: does it change what the thermal image shows?
- **AEE status**: NOT BUILT (documented, not implemented), IMPLEMENTED
  (wired, off-game tested), IN-GAME PROVEN (seen working by the user).
- **Proof**: the in-game observation or the mechanism.

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

## The baked / immutable layers (the engine ceiling)

These cannot be changed at runtime by any script.  They are the walls
the #204 investigation hit and proved.

| Layer | Why it is baked | Proof |
|---|---|---|
| Terrain surface texture | No runtime terrain-material swap exists; satellite `s_satout_co.paa` is a baked image | #204: all maps verified identical structure |
| Terrain/vegetation/rock heat | Only the second-sun term reaches them; no per-pixel control | #204: all vanilla flat decals report `tex=[] mats=[]` |
| Object-decal heat on terrain | Decals render as terrain projections the TI pass ignores | #204: Land_DirtPatch + drop billboards invisible in TI |
| The native TI renderer itself | Compiled, non-interceptable; ppEffects do not apply during vision mode 2 | #204: RPT showed handles created, never applied |
| Gen-1/2 weapon heat | `setVehicleTIPars` does not work on infantry weapons | Dossier section 2.3 |
| Infantry base body | Renders natively at a fixed ~33 C skin temperature | Dossier section 2.5 |

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
- In-game tests: the #204 RPT trail