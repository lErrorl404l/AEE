# The Arma 3 Engine Config Surface

Global roots, the override mechanisms, the ceilings, and the pattern to follow.

Compiled 2026-10-08. This document maps the engine config class tree so AEE
stops guessing the inheritance. Every engine claim carries its source and
line.

## 0. Evidence base

The engine core config is `Dta/bin.pbo`. The derapified copy read here is
`the derapified core engine config (Dta/bin.pbo)` (37,418 lines). The UI config is
`a3/ui_f.pbo`, derapified to `the derapified ui_f.pbo config`. The weapon
config is `a3/weapons_f.pbo`, derapified to `the derapified weapons_f.pbo config`.
The engine PBOs are under
`the Arma 3 install Addons/` (237 unpacked
`config.cpp`). Method for any other PBO:

```
hemtt utils pbo unpack <pbo> <dir>          # then
hemtt utils config derapify <dir>/config.bin # writes config.cpp BESIDE config.bin
```

Two facts frame everything. Config is **load-time and global**: a PBO's config
merges into the engine tree when the PBO loads, and the merge is
last-loaded-wins per property. Config cannot be gated at run time, so the PBO
is the only off switch (ADR-001, ADR-027). The engine's C++ runtime (simulation
solver, renderer, flight model, ballistic integrator, AI routing) is not
addressable by config or by script.

## 1. The global config roots

Each root is a top-level class in one engine config. Line numbers are in the
derapified sources named above.

| Root | Engine source | What it controls | Mod-reachable fields | Ceiling |
|---|---|---|---|---|
| `CfgVehicles` | bin.pbo:4593 | Every entity: units, cars, tanks, air, boats, buildings, props, animals, ammo boxes. | `scope`, `model`, `simulation`, `side`, `faction`, `mass`, `maxSpeed`, `armor`, `armorStructural`, `HitPoints`, `Wheels`, `complexGearbox`, `thrustDelay`, `brakeDistance`, `maxBrakeTorque`, `terrainCoef`, `crew`, `weapons[]`, `magazines[]`, `hiddenSelections*`, `DestructionEffects`, `class Turrets`, `class RenderTargets` | Physics keys load at load time. `armor` is a health pool, not a ballistic gate. No runtime FDM swap (ADR-017). |
| `CfgWeapons` | bin.pbo:3030 | Weapons, launchers, optics, items, binoculars, NVGs, headgear, uniforms. | `dispersion`, `recoil`, `maxZeroing`, `discreteDistance[]`, `magazineReloadTime`, `swayCoef`, `opticsZoomMin/Max/Init`, `opticsFlare`, `ItemInfo >> OpticsModes >> <mode>` with `thermalMode[]`, `thermalNoise[]`, `thermalResolution[]`, `model`, `picture` | `dispersion` is an engine cone, not a measured group. Thermal palette is the engine pair only (WHOT/BHOT). |
| `CfgAmmo` | bin.pbo:2429 | The projectile: bullets, shells, missiles, rockets. | `hit`, `caliber`, `typicalSpeed`, `airFriction`, `coefGravity`, `timeToLive`, `tracerScale/StartTime/EndTime`, `indirectHit`, `indirectHitRange`, `explosive`, `deflecting`, `visibleFire`/`audibleFire`, `dangerRadius*`, `suppressionRadius*`, `aiAmmoUsageFlags` | `hit` and `caliber` are a two-gate integer model, not a physical penetrator. |
| `CfgMagazines` | bin.pbo:2916 | Ammunition magazines. | `initSpeed` (muzzle velocity), `ammo`, `count`, `mass`, `tracersEvery`, `lastRoundsTracer`, `type`, `model` | None. Plain scalars. Cleanest override surface. |
| `CfgRecoils` | bin.pbo:2903 | Weapon recoil impulse curves. | The recoil array (time, x, y, z sequence) per named recoil | Fixed array shape. Engine owns the camera kick. |
| `CfgWorlds` | bin.pbo:14967 | Worlds, lighting, tone curve, grid, weather, map scale. | `mapSize`, `mapZone`, `mapArea[]`, `Grid` (relabel/respace/shift), `HDRNewPars`, `class Lighting: DefaultLighting`, `DayLightingBrightAlmost/Rainy`, `Weather`, `Overcast >> Weather1..6`, `DOFPars`, `DefaultClutter`, `starEmissivity`, `latitude`/`longitude`, `startTime`/`startDate` | Terrain heightmap, satellite raster and contour geometry are engine/map data, not config. Grid cannot be removed, only relabelled/respaced/shifted or alpha-zeroed. |
| `CfgSurfaces` | bin.pbo:10231 | Terrain material classes: friction, dust, sound, impact. | `friction`, `restitution`, `rough`, `dust`, `soundEnviron`, `character`, `impact`, `maxSpeedCoef`, `grassCover`, `surfaceFriction`, `tracksAlpha` | The surface-to-terrain mapping is baked in the map surface mask. Config reaches friction and dust only. |
| `CfgMarkers` | ui_f.cpp:89477 | Map marker visual definitions. | `name`, `icon`, `texture`, `color[]`, `size`, `shadow`, `scope`, `markerClass`, `showEditorMarkerColor` | Engine stretches the texture to the marker box and does not preserve aspect (feedback T170754). |
| `CfgMarkerClasses` | ui_f.cpp:90768 | Marker editor groups. | `displayName`, `scope`, `side` | Grouping only. |
| `CfgMarkerColors` | ui_f.cpp:90600 | Named marker colour entries. | `color[]`, `name`, `scope` | None. |
| `CfgLocationTypes` | ui_f.cpp:81444 | Map location labels (towns, hills, vegetation, areas). | `font`, `color[]`, `texture`, `size`, `textSize`, `name`, `shadow`, `drawStyle`, `coefMin`, `coefMax` | `drawStyle` is a fixed engine enum (`area`, `name`, and similar). Unknown value logs `Wrong location draw style`. Object-to-icon routing is engine-internal (T157884). |
| `RscMapControl` and the UI classes | ui_f.cpp:1272 | The in-game map, minimap, strategic map, Eden map, every display control. | Every map palette field: `colorLevels`, `colorCountlines`, `colorSea`, `colorForest`, `colorForestTextured` (ctrlMap only), `colorRocks`, roads/rail/power/tracks, `colorGrid`, `fontGrid`, `sizeExGrid`, `maxSatelliteAlpha`, `alphaFade*`, `drawShaded`, `shadedSea`, `showCountourInterval`, `ptsPerSquare*` | Contour geometry and interval are engine-derived. Satellite raster is baked per world. No hypsometric tint ramp. `RscDisplayStrategicMap >> controlsBackground >> Map` and Eden `ctrlMap` need their own re-declare. |
| `CfgCloudlets` | bin.pbo:3585 | Particle effects: smoke, dust, explosion, fire. | `particleShape`, `particleType`, `interval`, `lifeTime`, `moveVelocity[]`, `weight`, `volume`, `rubbing` (wind/downwash coupling), `size[]`, `color[]`, `animationSpeed[]`, `randomDirection*`, `onTimerScript`, `beforeDestroyScript` | New cloudlets are free. The particle solver is engine-closed. |
| `CfgLights` | bin.pbo:4225 | Dynamic light definitions. | `color[]`, `ambient[]`, `diffuse[]`, `brightness[]`, `intensity`, `blinking`, `drawLight`, `position[]`, `class Attenuation { start; constant; linear; quadratic; }` | The light list loads once. A per-object light cannot be added at run time. |
| `CfgEnvSounds` / `CfgEnvSpatialSounds` | bin.pbo:14575, sounds_f | Environment ambience and per-model-memory-point sound binding. | `soundSetEnvironment[]`, `CfgEnvSpatialSounds >> <memPoint> >> soundSets[]` | A global environment list, not per biome. AEE biome logic is runtime. |
| `CfgMovesBasic`, `CfgMovesMaleSdr`, `CfgMovesAnimal`, `CfgGesturesMale` | bin.pbo:8302/8384, anims_f, animals_f | Animation state graphs, transitions, timing. | Per-state `file`, `speed`, `interpolateTo[]`, `interpolateFrom[]`, `connectTo[]`, `variantsPlayer[]`, `variantsAI[]`, `actions` | Value-only reopen changes timing, not motion. An animation override needs a matching `.rtm` asset and skeleton. Asset-gated. |
| `CfgGroups` | data_f:5246 (defined), bin.pbo:17026 (forward decl) | Eden/Zeus order-of-battle groups per faction. | Group `name`, `faction`, member `side`, `vehicle`, `rank`, `position[]` | None at config level. |
| `CfgFactionClasses` | bin.pbo:4305, data_f, modules_f | Faction display names, sides, priorities. | `displayName`, `side`, `priority`, `icon` | None. |
| `CfgCurator` | bin.pbo:842, ui_f.cpp:79239 | Eden and Zeus icons: group, camera, editing area. | `DrawGroup >> textureWest/East/Guer/Civilian/Unknown`, `DrawGroup >> 3D/2D`, `EditingArea`, `DrawCamera` | Icons are per side, not per unit function. The object tree and unit icons are engine-internal. |
| `CfgOpticsEffect` | bin.pbo:3990 (forward decl), data_f | Optics post-process effects. | `type` (ColorCorrections, dynamicblur, radialblur, chromaberration, FilmGrain, colorInversion), `priority`, `params[]` | `priority` ordering is global. A reopen changes every use of the effect. |
| `CfgVehicleIcons` | bin.pbo:8549, ui_f.cpp:81347 | Named editor/timeline icon paths. | Named keys: `iconModule`, `IconTimeline`, `IconCurve`, `IconKey`, `IconControlPoint`, `IconCamera` | Object-to-icon routing is engine-internal. Keys the engine does not read are inert. |
| `CfgFontFamilies` | bin.pbo:10349 | Font families for map, HUD and UI text. | `fonts[]` (per-size glyph files), `spaceWidth` | Asset-gated. The family is inert until `.fxy`/`.paa` glyph files exist. FontToTGA needs Windows. |
| `CfgMaterials` / `CfgTextureToMaterial` | bin.pbo:2074 / 2046 | RVMAT material names and texture-to-material routing. | `CfgMaterials` keys, `CfgTextureToMaterial` texture-to-material map | The renderer resolves materials at load. A scripted material swap is a different mechanism. |
| `CfgCloudletShapes` | bin.pbo:8576 | Particle shape definitions. | shape name and texture keys | Engine particle solver. |
| `CfgSoundSets`, `CfgSoundShaders`, `CfgSFX` | sounds_f | Audio sets, shaders, 3D processing. | `soundShaders[]`, `volumeFactor`, `volumeCurve`, `frequencyRandomizer`, `volumeRandomizer`, `spatialityRange`, `sound3DProcessingType`, `spatial`, `doppler`, `speedOfSound`, `loop` | None at config level for new sets. |
| `DestructionEffects` (nested) | bin.pbo:4593 and per vehicle | Wreck and hit FX. Not a top-level class. | `simulation = "particles"`, `type` (a cloudlet), `position` (named selection), `intensity`, `interval`, `lifeTime`, `ammoExplosionEffect` | Fires on the engine destruction event only. AEE cannot add a trigger. |

### Further realism-relevant roots

These are top-level in `bin.pbo` and reachable. They carry physiology, AI and
weapon-handling realism that AEE reads or should read.

| Root | Line | Controls |
|---|---|---|
| `CfgFatigue` | 8082 | Stamina drain and recovery coefficients. |
| `CfgFirstAid` | 8089 | Medical revive and healing parameters. |
| `CfgDiving` | 8142 | Diving depth and physiology. |
| `CfgBleeding` | 8175 | Bleeding rates. |
| `CfgImprecision` | 8193 | Weapon dispersion and aim imprecision model. |
| `CfgBreathing` | 8245 | Breathing hold and sway. |
| `CfgWeaponHandling` | 8252 | Weapon inertia, raising and lowering. |
| `CfgAISkill` / `CfgAILevelPresets` / `CfgBrains` | 331/344/2019 | AI skill, accuracy and FSM selection. |
| `CfgPersonTurret` | 8296 | Firing from a vehicle turret. |
| `CfgSkeletonParameters`, `CfgRagDollSkeletons` | 8192/8921 | Skeleton and ragdoll. |
| `CfgMineTriggers` | 2382 | Mine trigger classes. |
| `CfgSurfaceCharacters` | 10223 | Surface character classifiers. |
| `CfgCoreData` | 8500 | Core data records. |
| `CfgEditorObjects` | 17032 | Eden placeable object list. |

## 2. The override mechanisms, exactly

### 2.1 `class X : Y` — the inheritance operator

`class X : Y { ... }` declares X with Y as its parent. X inherits every field
of Y and overrides only the fields it names. This is the only way to override a
vanilla class and keep its inherited fields.

### 2.2 The bare-reopen trap and the parent restatement rule

A bare reopen is `class X { ... }` with no `: Y`. The engine treats it as a
class with **no parent**. It logs

```
Updating base class '<parent>'->''
```

and X loses every field it inherited: `scope`, `size`, `drawStyle`,
`markerClass`, `texture`, and all the rest. This is the defect that produced
`No entry CfgMarkers/*.scope` and `Wrong location draw style` in AEE's RPT.

The rule is the **parent restatement rule**. When you reopen a vanilla class,
you must name its real engine parent:

```
class b_inf: b_unknown { ... };   // correct
class b_inf { ... };              // defect: strips b_unknown
```

The inverse also applies. When the vanilla class has **no** parent, you must
**not** add one. Adding a parent logs

```
Updating base class ''->'<name>'
```

and rebases the class. AEE's `HDRNewPars`, `DOFPars` and `DefaultLighting`
carry no vanilla base, so they are reopened bare. `Mount`, `Name` and `Area`
in `CfgLocationTypes` are likewise parentless and stay bare, exactly as
`ui_f.cpp` declares them.

AEE enforces the rule mechanically.
`tools/tests/test_config_inheritance.py` fails any reopen that does not name
the engine parent, and fails any rebase of a parentless class.
`tools/validation/validate_engine_overrides.py` rejects a bare reopen in a
generated header.

### 2.3 Forward declaration

`class Y;` declares a name so a later `class X : Y` can resolve even when Y is
declared in another addon. The declaration must sit at the **same scope** as
the class that uses it.

A **file-root** forward declaration is a trap. `class Y;` at column zero of a
config PBO makes the engine create an empty class Y and re-parent every
existing map entry onto it, destroying the real definition. A **nested**
declaration merges with the engine's definition at that path and is safe. AEE
generates forward declarations for external parents inside the block
(`class ItemCore;`, `class InventoryOpticsItem_Base_F;`) and the inheritance
test forbids a file-root declaration of the world classes.

HETT reports the two failure modes as `L-C03` (a class is both forward-declared
and defined) and `L-C04` (a parent is not present).

### 2.4 Last-loaded-wins

The config merge is **per property**, not per class. If two PBOs both set
`showEditorMarkerColor` on the same class, the later-loaded value wins. Load
order decides everything in the absence of a declared dependency.

### 2.5 `requiredAddons` and load order

`CfgPatches >> <addon> >> requiredAddons[]` declares the addons that must load
before this one. The engine loads them first, so the declaring addon's values
win. AEE declares the base addons:

```
requiredAddons[] = { "A3_Data_F", "cba_main", "cba_xeh" };
```

The base game always loads first, so every class AEE re-declares wins over the
base game. Over a **known host mod**, a compat PBO declares the host in
`requiredAddons[]` and carries `skipWhenMissingDependencies = 1`. The engine
then loads the compat PBO only when the host is present, and the compat values
win. Over an **undeclared** mod only mod-list order decides the merge. That is
a ceiling to detect and log, not a defect to chase (ADR-027).

`requiredVersion` gates the **engine** version, not a mod version. AEE sets it
from `REQUIRED_VERSION`.

### 2.6 Case-insensitive class names

Class names resolve **case-insensitively**. `Church` (engine core) and `church`
(ui_f) are the same class. An added capitalised alias is a duplicate, not a new
class, and HETT rejects it. This was proved by HETT `L-C03` during the map
legibility work.

### 2.7 Definition order inside a file

Within a file, a parent must be resolved before a child that inherits it. AEE's
marker generator sorts parents before children before it emits the header.

## 3. Engine-internal, unreachable from a mod

These are closed. No config field and no script command reaches them. Evidence
is stated per item.

| Item | Evidence |
|---|---|
| Simulation solver and ballistic integrator | ADR-017. `CfgAmmo` sets initial values, the engine integrates. |
| Vehicle flight dynamics model | ADR-017. No runtime FDM swap, no `setFlightModel`. CMass and speed are load-time only. |
| Renderer | ADR-027. Materials resolve at load. |
| AI routing and object-to-icon routing | ADR-029, feedback T157884. The engine decides which icon a map object uses. |
| Contour geometry and contour interval | ADR-029. Only the colour and the `showCountourInterval` label are config. |
| Satellite raster | ADR-029. Baked per world. `pictureMap` and blend fields tune it, they do not replace it. |
| Hypsometric tint ramp | ADR-029. No field exists. |
| `drawStyle` enum | ADR-029. Fixed set. An unknown value logs `Wrong location draw style`. |
| Thermal palettes beyond WHOT/BHOT | Engine holds only the two palettes. |
| Marker texture aspect | Feedback T170754. The engine stretches to the marker box. |
| Engine legend body | The engine legend class holds no body. AEE scripts its own, like the MGRS overlay. |
| Font family until glyphs ship | Asset-gated. The config is inert without `.fxy`/`.paa`. |
| Eden/Zeus object-tree icons | `CfgCurator` gives per-side textures only. Per-unit-function glyphs are engine-internal. |
| Animation motion | Asset-gated. A value reopen changes timing, not a missing `.rtm`. |

## 4. The pattern for any config change

Follow these eight steps. They are the AEE house pattern and the generators
already embody them.

1. **Read the engine.** Find the vanilla class and its real parent in the
   derapified config (`bin.pbo`, then the addon PBO). Never guess the parent.
2. **Restate the parent.** Reopen as `class X: <realParent>`. If the vanilla
   class is parentless, reopen bare and never rebase it.
3. **Override only your values.** Name the fields AEE owns. Name no other
   field, so the engine's values survive.
4. **Forward-declare external parents at the correct nested scope.** Never
   declare a class at the file root.
5. **Generate from a cited corpus.** A generator emits the header from data
   with a source per value. The header states "do not edit by hand".
6. **Pin the value with a test.** A unit test asserts the parent is restated,
   the key is present, and the value matches its source. A probe asserts the
   merged config at run time.
7. **Declare the dependency.** Add the base addon or the host mod to
   `requiredAddons[]`. Add `skipWhenMissingDependencies = 1` for an optional
   host.
8. **Record the ceiling.** When the engine cannot be reached, record the
   ceiling and the evidence, so the next worker does not retry it.

The template is `addons/mobility/generated/CfgVehicles.hpp` and
`addons/thermal/generated/ThermalOptics.hpp`: a generator, a
"do not edit" header, and a `--check` gate in the Makefile.

## 5. Sources

- Engine configs: `the derapified core engine config (Dta/bin.pbo)`,
  `the derapified ui_f.pbo config`, `the derapified weapons_f.pbo config`.
- Engine PBOs: `the Arma 3 install Addons/`.
- AEE: `docs/adr/ADR-001-engine-anchors.md`, `ADR-017-flight-physics-ceiling.md`,
  `ADR-027-ownership-architecture.md`,
  `ADR-029-marker-derivation-from-the-engine-config.md`,
  `ADR-030` (map legibility),
  `tools/tests/test_config_inheritance.py`,
  `tools/validation/validate_engine_overrides.py`,
  `docs/wiki/research/engine-override-surface.md`.
- Prior domain study: `engine-override-surface.md`,
  `topo-map-surface.md`.

Budget note: this is a forced-long report. The task named about twenty roots
plus four mechanism sections. It is about 2,600 words. The supporting reads
were about 25 tool calls over the derapified engine configs, the AEE tests,
and the prior domain studies.
