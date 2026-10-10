# The baked-texture and terrain override surface (issue #128)

Compiled 2026-10-10. The engine facts behind AEE's control of baked textures,
map layers and per-component vehicle parts, each with its evidence. Every claim
names a PBO and a field; no path on one machine.

## 0. Why this document exists

Issue #128 asks how far AEE reaches into baked (non-config) visuals: the TI
textures the renderer composites, the terrain layer materials, and the
per-component parts of a vehicle. The answer is the three override mechanisms
of ADR-001, each with a real ceiling. This document records what was VERIFIED
against the installed engine, and what stays out of reach.

Method: read the unpacked engine PBOs directly. To reproduce any source:

```
hemtt utils pbo unpack <pbo> <outdir>
hemtt utils config derapify <outdir>/config.bin
```

Sources read: `data_f` (default materials), `map_altis_data_layers` (terrain
layer materials), the derapified core engine config `Dta/bin.pbo` (CfgSurfaces,
CfgMaterials). The engine PBO inventory is
[engine-pbo-inventory.md](engine-pbo-inventory.md).

## 1. The three override mechanisms (ADR-001)

| Mechanism | What it controls | Cost | Reversible at run time |
|---|---|---|---|
| PBO path override | A baked texture or material at a vanilla path | Load time, global, last-loaded wins | No (the PBO is the switch) |
| Config override | Values and materials for a known class, no model edit | Load time, global | No |
| Runtime anchor | A material or texture on a named selection | Per call, client-local | Yes |

The runtime anchor is the only mechanism AEE drives from script. The other two
are load-time and need a shipped asset or a model whose selections are known.

## 2. Layer 1: baked TI textures

### 2.1 The shared default TI material (VERIFIED)

An object with no dedicated thermal map falls back to a shared default
material. In the `data_f` PBO:

- `a3\data_f\default.rvmat` declares `class StageTI { texture =
  "a3\data_f\default_vehicle_ti_ca.paa"; }`.
- `a3\data_f\default_TI.rvmat` declares `class StageTI { texture =
  "a3\data_f\default_ti_ca.paa"; }`.

Both files carry the same shader pair (`PixelShaderID = "Normal"`,
`VertexShaderID = "Basic"`) and differ only in the StageTI texture path.

The fallback TI map is `a3\data_f\default_vehicle_ti_ca.paa`. It is present in
`data_f`. The texture named by `default_TI.rvmat` (`a3\data_f\default_ti_ca.paa`)
is NOT present in the unpacked `data_f` PBO.

Consequence: a PBO path override of `a3\data_f\default_vehicle_ti_ca.paa`, or of
`a3\data_f\default.rvmat` itself, changes the thermal appearance of every object
that falls back to the shared default. That is the "master lever" the issue
names. It is a LOAD-TIME, GLOBAL change: it cannot be gated per object, and the
PBO is the only off switch.

### 2.2 PBO path override mechanics and its ceiling

The config merge is per property and last-loaded wins
([engine-config-surface.md](engine-config-surface.md), section 2.4). A file
override follows the same rule: two PBOs that carry a file at the same virtual
path, the later-loaded one wins. A PBO's files are rooted at its
`$PBOPREFIX$`, so to reach a vanilla path a mod ships a PBO whose prefix or
internal path resolves to that path. AEE builds under `z\aee\addons\`, so it
does not collide with the vanilla `a3\` tree by default; a deliberate override
would need a PBO that mounts at the vanilla path. Whether that PBO loads after
`data_f` for a given host mod list is decided by load order, not by AEE. The
exact per-host outcome is **UNKNOWN** without an in-engine run.

### 2.3 Config material override

`hiddenSelectionsMaterials[]` on a class adds materials to a class that had
none, with no model edit. The engine reads it per selection. The ceiling: the
selection must exist in the P3D. AEE cannot verify a model's selections without
the model, so this path is not exercised by AEE's script; it is available to a
generated config over a class whose selections are held.

## 3. Layer 2: terrain

### 3.1 CfgSurfaces has no rvmat field (VERIFIED)

`CfgSurfaces` (derapified core config `Dta/bin.pbo`) defines surface BEHAVIOUR.
The `Default` class carries: `files`, `rough`, `dust`, `lucidity`, `isWater`,
`maxSpeedCoef`, `friction`, `restitution`, `soundEnviron`, `character`,
`impact`, `grassCover`, `surfaceFriction`, `tracksAlpha`, `transparency`,
`AIAvoidStance`. There is no `rvmat`, `texture` or `material` field. A
`CfgSurfaces` override therefore reaches friction, dust and sound, never the
terrain's rendered material.

### 3.2 The WRP layer materials (VERIFIED)

The terrain's rendered material is the WRP layer RVMAT. In the
`map_altis_data_layers` PBO they live at
`a3\map_altis\data\layers\P_XXX-YYY_L00.rvmat` (one per terrain cell, 14736
files for Altis). Each layer material declares:

- `PixelShaderID = "TerrainSNX"`, `VertexShaderID = "Terrain"`.
- `Stage0` texture `a3\map_data\tiled_s_co.paa`, `Stage1` texture
  `a3\map_data\tiled_m_co.paa` (the surface and mid-detail maps), plus seabed,
  normal and detail stages.

Consequence: shipping a replacement `.rvmat` at a layer path is a PBO path
override (section 2.2) and changes the terrain's rendered appearance, including
its thermal response. The layer texture paths are shared (`a3\map_data\tiled_*`),
so a replacement at the layer path changes appearance without touching the
shared detail maps.

### 3.3 The GDT surface mask (ceiling)

The surface-type mask (which `CfgSurfaces` class applies at each terrain cell)
is baked into the WRP, not into config. It is runtime-immutable: no config field
and no script reaches it. A change needs a re-binarised map. This is the same
ceiling `docs/engine/engine-override-surface.md` records for `CfgSurfaces`.

## 4. Layer 3: the runtime anchor (AEE's path)

The engine exposes named selections and hit points as fixed anchors
(`selectionNames`, `getAllHitPointsDamage`), and `setObjectMaterial` /
`setObjectTexture` apply a material or texture to one selection by index. AEE
drives all per-component control through this path:

- The component anchor registry (issue #128) maps a component ROLE (engine,
  wheel, turret, glass) to the model selections that name that part, from the
  hit points (guaranteed) and the selection names.
- `setObjectMaterial` selects an EXISTING `.rvmat`; it cannot define a custom
  shader or a per-object material program.

## 5. Consolidated ceilings

What a PBO override (or any AEE path) cannot reach:

1. The GDT surface-type mask. Baked in the WRP; runtime-immutable.
2. Glass thermal reflections. Model-baked; a custom model is required.
3. Per-pixel temperature. The engine composites per material, not per pixel.
4. The thermal pass renderer. Not interceptable; the palette is engine-fixed.
5. A custom shader or per-object material program. Materials come from existing
   `.rvmat` assets only.
6. A config material override on a selection the P3D does not name.
7. The load order of an undeclared host mod. Decided by the mod list, not AEE.
8. The per-host outcome of a vanilla-path PBO override without an in-engine run.

## 6. Sources

- Engine PBOs: `data_f` (default.rvmat, default_TI.rvmat,
  default_vehicle_ti_ca.paa), `map_altis_data_layers` (the layer RVMATs),
  `Dta/bin.pbo` (CfgSurfaces, CfgMaterials).
- AEE: `docs/adr/ADR-001-engine-anchors.md`,
  [engine-config-surface.md](engine-config-surface.md),
  [engine-override-surface.md](engine-override-surface.md),
  [engine-pbo-inventory.md](engine-pbo-inventory.md).
- The command surface for the runtime anchors:
  [engine-commands-and-features.md](engine-commands-and-features.md).
