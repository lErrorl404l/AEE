# The engine override surface: AEE's authority over base-game config classes

Compiled 2026-10-08. Every class verdict carries its evidence.

## 0. Why this document exists

AEE already re-declares base engine classes in place: `CfgWorlds` HDR and
DayLighting, `CfgMarkerColors` and the engine `CfgMarkers`, `CfgLocationTypes`,
`RscMapControl`, the display classes and `CfgCurator`. The principle works. The
operator asks how far it reaches. This document enumerates the engine config
classes a mod can override, organises them by domain, and gives a verdict per
class.

The override is a **load-time, global substitution**. The engine reads the
config when the PBO loads. Config cannot be gated at run time. The PBO is the
only off switch. This is the same fact that the generated mobility header
states (`addons/mobility/generated/CfgVehicles.hpp`, header comment).

### The three override mechanisms (ADR-001)

Every override reaches the world by one of three mechanisms. The order is the
order of increasing runtime cost.

| Mechanism | What it controls | AEE example |
|---|---|---|
| **PBO path override** | Baked textures, terrain layers, default TI. Ship a replacement `.paa`/`.rvmat` at the vanilla path. Last-loaded wins. | `\A3\data_f\default.rvmat` |
| **Config override** | Values, materials, inheritance for known classes. No model change. | `CfgVehicles >> Land_Rock_01_F { hiddenSelectionsMaterials[] = {...}; }` |
| **Runtime anchor** | Per-component state through named selections, hitpoints, memory points. | `setObjectMaterial` in `fnc_applyWeaponBarrelHeat` |

Source: `docs/adr/ADR-001-engine-anchors.md`.

### The verdict legend

| Verdict | Meaning |
|---|---|
| **ADOPT** | AEE does not override it. It can, it should, and a realistic value exists. |
| **ALREADY** | AEE overrides it today. The override is sound. Keep it. |
| **RECONCILE** | AEE overrides it, but the value, the scope, or the class name needs review. |
| **REJECT** | The class cannot be overridden usefully, or the override is out of scope. State the ceiling. |

### The ceiling taxonomy

A ceiling is a real limit, not a convention. Each REJECT names its ceiling type.

- **Load-time**: no runtime command. The PBO is the switch.
- **Engine-internal routing**: the engine decides which class a feature uses.
  No config field reaches it.
- **Per-scope**: the engine reads the field per side, per display, or per
  world, not per unit or per instance.
- **Renderer/solver**: the engine resolves the model at load. A scripted layer
  cannot replace it.
- **Asset-gated**: the field is inert until a companion binary asset ships.

---

## 1. Where the base classes live (evidence base)

A full Arma 3 install carries about 237 unpacked `config.cpp` files plus
packed PBOs. The base configs read for this study were the derapified copies
of the weapon and UI addons. The relevant config-to-file mapping:

| Config | File |
|---|---|
| `CfgAmmo`, `CfgMagazines`, `CfgWeapons`, `CfgRecoils`, `CfgMagazineWells` | `weapons_f.pbo` |
| `CfgMarkers`, `CfgMarkerColors`, `CfgMarkerClasses`, `CfgLocationTypes`, `CfgCurator`, `CfgVehicleIcons`, `RscMapControl` | `ui_f.pbo` |
| `CfgCloudlets`, `CfgLights`, `CfgOpticsEffect`, `CfgMuzzleFlashes`, `CfgCameraShake`, `CfgWeaponHandling`, `CfgImprecision`, `CfgSurfaces`, `CfgWorlds` | `data_f/a3/data_f/config.cpp`, `data_f/a3/data_f/ParticleEffects/config.cpp` |
| `CfgSoundSets`, `CfgSoundShaders`, `CfgSFX`, `CfgEnvSounds`, `CfgSoundCurves`, `CfgDistanceFilters`, `CfgSound3DProcessors`, `CfgDestroySounds` | `sounds_f/a3/sounds_f/config.cpp` |
| `CfgWorlds` (world) | `map_altis/a3/map_altis/config.cpp`, `map_data`, `map_stratis`, `map_vr` |
| `CfgVehicles` | `armor_f`, `air_f`, `boat_f`, `data_f`, and the rest of the unpacked set |

Method: `hemtt utils pbo extract <pbo> config.bin <out>` then
`hemtt utils config derapify -f cpp <out> <out.cpp>`.

---

## 2. Tier 1: the highest realism impact

### 2.1 `CfgAmmo` (ballistics: drag, tracer, penetration, fragmentation)

- **Class path**: `CfgAmmo >> <ammoClass>`, base `BulletBase`/`ShellBase`/
  `MissileBase`.
- **What overriding changes**: the projectile's whole physical model. `hit`
  (penetration term), `caliber` (armour gate), `typicalSpeed`, `airFriction`
  (drag), `coefGravity`, `timeToLive`, `tracerScale`/`tracerStartTime`/
  `tracerEndTime`, `indirectHit`/`indirectHitRange`, `explosive`, `deflecting`,
  `visibleFire`/`audibleFire`, `dangerRadius*`/`suppressionRadius*`,
  `aiAmmoUsageFlags`, `waterFriction`.
- **AEE status**: **not overridden at config level**. AEE resolves ballistics
  at run time (`addons/ballistics/functions/fnc_resolveShot.sqf`,
  `fnc_calculateBallisticDrag.sqf`, `fnc_calculateCrosswindBallistics.sqf`) from
  its own cited database. Base sample: `B_556x45_Ball { hit = 9; typicalSpeed =
  920; airFriction = -0.0012; caliber = 0.869565; }`.
- **Realistic value**: per-cartridge. AEE holds 677 cartridges with pressure,
  twist and grooves (`data/ballistics/INDEX.md`, source CIP TDCC under
  `data/ballistics/sources/cip/`). The BC and drag model is derived, never
  copied from mod data (ADR-003).
- **Ceiling**: the engine's `hit`/`caliber` are a two-gate integer model, not a
  physical penetration solver (`docs/wiki/research/vehicle-armour-research.md`
  §1). A config override cannot make the gate physical. **ADOPT with caution**:
  a load-time override of `airFriction` and `typicalSpeed` per cartridge is
  possible and would move the engine's own trajectory; AEE chose the runtime
  kernel instead. The two approaches must not both own the same key.

### 2.2 `CfgMagazines` (muzzle velocity, tracer ratio, round count)

- **Class path**: `CfgMagazines >> <magClass>`.
- **What overriding changes**: `initSpeed` (muzzle velocity), `ammo` (the
  projectile), `count`, `mass`, `tracersEvery`, `lastRoundsTracer`, `type`.
  Base sample: `30Rnd_556x45_Stanag { ammo = "B_556x45_Ball"; count = 30;
  initSpeed = 920; tracersEvery = 0; lastRoundsTracer = 4; }`.
- **AEE status**: **not overridden**.
- **Realistic value**: the real cartridge muzzle velocity from a cited load
  table (`data/ballistics/loads.json`), and the real tracer ratio (commonly
  every fifth round, or belt-dependent).
- **Ceiling**: none at config level. This is the cleanest ADOPT in the
  ballistics domain: `initSpeed` and `tracersEvery` are plain scalars.
  **ADOPT**.

### 2.3 `CfgWeapons` (dispersion, recoil, zeroing, optics)

- **Class path**: `CfgWeapons >> <weaponClass>`; optics under
  `CfgWeapons >> <opticClass> >> ItemInfo >> OpticsModes >> <mode>`.
- **What overriding changes**: `dispersion` (cone of fire), `recoil` (the
  `CfgRecoils` entry), `maxZeroing`, `discreteDistance[]`,
  `magazineReloadTime`, `swayCoef`, `opticsZoomMin`/`opticsZoomMax`/
  `opticsZoomInit`, `opticsFlare`, `opticsDisablePeripherialVision`,
  `weaponInfoType`, and the per-mode thermal keys `thermalMode[]`,
  `thermalNoise[]`, `thermalResolution[]`.
- **AEE status**: **partly overridden**. `addons/thermal/generated/
  ThermalOptics.hpp` re-declares `optic_Nightstalker`, `optic_tws`,
  `optic_tws_mg` and sets the thermal keys per mode. Base `optic_tws >> TWS`
  carries `thermalMode[] = {0,1}` and no noise/resolution.
- **Realistic value**: `thermalNoise[]` = detector NETD in Celsius, from the
  device corpus (`data/device/catalogue/thermal_devices.json`).
  `thermalResolution[]` = detector pixel array. Both derived, no mod value
  copied. Dispersion and recoil have real sources but are not yet bound.
- **Ceiling**: `dispersion` is a cone in the engine, not a measured group size.
  `thermalMode[]` is the engine-minimum palette pair (WHOT 0, BHOT 1); the
  engine holds no third palette (`docs/wiki/research/engine-thermal-
  mechanisms.md`). **ALREADY** for the thermal keys. **ADOPT** for
  `dispersion`, `maxZeroing` and `recoil` binding from the ballistics corpus.

### 2.4 `CfgVehicles >> armor` and `HitPoints` (protection)

- **Class path**: `CfgVehicles >> <vehClass>`; per-location under
  `HitPoints >> HitHull/HitEngine/HitGlass*/...`.
- **What overriding changes**: `armor` (the health pool, integer),
  `armorStructural`, per-hitpoint `armor` (float multiplier), `material`,
  `visual`, `passThrough`, `explosionShielding`, `minTotalDamageThreshold`.
- **AEE status**: **not overridden statically, by design**. `addons/armour/
  config.cpp` documents why: rebasing a class discards fields the engine reads
  from the real base, so AEE resolves protection dynamically
  (`fnc_getVehicleArmour`, `fnc_deriveProtection`, `fnc_penetrationGate`).
- **Realistic value**: STANAG 4569 protection levels L1 to L6 (4-5 mm to
  100 mm+ RHAe). Real vehicles: MRAP to L3, IFV L4/L5, MBT L6. Source:
  `docs/wiki/research/vehicle-armour-research.md` §2.
- **Ceiling**: `armor` is a health pool, not a ballistic gate. The formula
  `(HIT*HIT)/Armor * (0.27/tgtRadius)^2` depletes with hits and is independent
  of the bisurf penetration gate. Raising it makes the pool deeper, not
  impenetrable. **ALREADY** (dynamic) and **RECONCILE**: a load-time
  `HitPoints >> armor` multiplier per location is available and would let AEE
  scale the pool from the STANAG table without discarding the base class.

### 2.5 `CfgWorlds` (weather, lighting, map scale)

- **Class path**: `CfgWorlds >> DefaultWorld / CAWorld / <world> / Altis`.
- **What overriding changes**: `mapSize`, `mapZone`, `mapArea[]`, the
  `HDRNewPars` tone curve, `DayLightingBrightAlmost`/`DayLightingRainy`
  keyframes, `Lighting >> starEmissivity`, `Weather >> LightingNew` and
  `Overcast >> Weather1..6`, `DOFPars`, `Grid` (relabel respace shift),
  `DefaultClutter`.
- **AEE status**: **ALREADY**. `addons/lighting/config.cpp` re-declares
  `DefaultLighting`, `DefaultWorld`, `CAWorld`, `Stratis`; sets
  `starEmissivity = 25` (vanilla), the `HDRNewPars` block and the two
  DayLighting keyframes. `addons/cartography/config_mapdisplays.hpp` sets the map
  colours.
- **Realistic value**: `starEmissivity` = vanilla 25 (the reference mod dims to
  20; AEE matched vanilla). The tone curve is global, so AEE treats it with
  care. Source: `docs/wiki/research/lighting-reference-review.md`.
- **Ceiling**: the terrain heightmap, satellite imagery and contour geometry
  are terrain data, not config. Only the colours and the interval label are
  config surfaces (`config_mapcolors.hpp` header). The `Grid` class can only
  relabel, respace and shift the grid; it cannot remove it (suppress by
  alpha-zeroing `colorGrid`/`colorGridMap` and blanking `fontGrid`/
  `sizeExGrid`). **ALREADY**.

### 2.6 `CfgOpticsEffect` (optics post-process: blur, aber, colour)

- **Class path**: `CfgOpticsEffect >> <effectClass>`.
- **What overriding changes**: `type` (ColorCorrections, dynamicblur,
  radialblur, chromaberration, FilmGrain, colorInversion), `priority`,
  `params[]`. Base classes include `TankGunnerOptics1/2`,
  `TankCommanderOptics1`, `BWTV`, `WeaponsOptics`, `OpticsBlur1..3`,
  `OpticsRadialBlur1..3`, `OpticsCHAbera1`.
- **AEE status**: **not overridden at config level**. AEE applies optics
  effects through runtime `ppEffect` calls and its own NVG/thermal pipeline.
- **Realistic value**: a blur radius and a chromatic-aberration offset bounded
  by the human-vision model (`docs/wiki/research/human-vision-model.md`,
  ADR-014).
- **Ceiling**: `priority` ordering is engine-global; a config override changes
  every use of the effect. **RECONCILE**: keep the runtime path, but the class
  is available if AEE wants the engine to apply the effect without a per-frame
  script call.

---

## 3. Tier 2: strong realism impact

### 3.1 `CfgLights` (dynamic light sources)

- **Class path**: `CfgLights >> <lightClass>`.
- **What overriding changes**: `color[]`, `ambient[]`, `diffuse[]`,
  `brightness`, `intensity`, `blinking`, `drawLight`, `position[]`, and
  `class Attenuation { start; constant; linear; quadratic; }`.
- **AEE status**: **not overridden**. AEE sets lights at run time.
- **Realistic value**: an inverse-square attenuation from the source's real
  luminous intensity. The base `SmallFireLight` uses `quadratic = 32`;
  `SmallFirePlaceLight` uses `quadratic = 22`.
- **Ceiling**: the light list is loaded once. A per-object light cannot be
  added at run time through config. **ADOPT**: a config light per fire/flare
  class is available and cheap.

### 3.2 `CfgCloudlets` (particle definitions)

- **Class path**: `CfgCloudlets >> <cloudletClass>`, base `Default`.
- **What overriding changes**: `particleShape`, `particleType`, `interval`,
  `lifeTime`, `moveVelocity[]`, `weight`, `volume`, `rubbing` (wind and
  downwash coupling), `size[]`, `color[]`, `animationSpeed[]`,
  `randomDirection*`, `onTimerScript`, `beforeDestroyScript`, `positionVar`,
  `MoveVelocityVar`.
- **AEE status**: **ALREADY**. `addons/core/config.cpp` declares
  `AEE_SandCloud` and `AEE_SnowCloud`; `addons/fx/config.cpp` declares
  `AEE_SupersonicTrace`. Both forward-declare `class Default;` to avoid
  shadowing the vanilla base.
- **Realistic value**: the particle physics and the wind/downwash coupling are
  specified in `docs/wiki/research/particle-array-spec.md`. The
  rotor-downwash brownout is in `docs/wiki/research/rotor-downwash-brownout.md`.
- **Ceiling**: none at config level for new cloudlets. **ALREADY**. **ADOPT**
  for re-authoring the vanilla smoke/dust cloudlets AEE currently only reads.

### 3.3 `CfgSoundSets` / `CfgSoundShaders` / `CfgSFX` (audio)

- **Class path**: `CfgSoundSets >> <set>`, `CfgSoundShaders >> <shader>`,
  `CfgSFX >> <sfx>`, `CfgEnvSounds`.
- **What overriding changes**: `CfgSoundSets`: `soundShaders[]`,
  `volumeFactor`, `volumeCurve`, `frequencyRandomizer`, `volumeRandomizer`,
  `spatialityRange`, `spatialityRangeAngle`, `sound3DProcessingType`, `spatial`,
  `doppler`, `speedOfSound`, `loop`. `CfgSFX`: `sound0[]..soundN[]`, `sounds[]`,
  `empty[]`. `CfgEnvSounds`: `soundSetEnvironment[]` and
  `CfgEnvSpatialSounds >> <memPoint> >> soundSets[]`.
- **AEE status**: **not overridden**. AEE's audio is runtime
  (`addons/wildlife`, `addons/radio`).
- **Realistic value**: the engine's own `CfgEnvSpatialSounds` binds a model
  memory point to a sound set. AEE's wildlife corpus
  (`docs/wiki/research/wildlife-sound-inventory.md`) and the wildlife ambience
  dossier supply species and habitat sound sets. The `CfgSFX` distance and
  volume curves are the engine's spatial model.
- **Ceiling**: `CfgEnvSounds` is a global environment list; it is not per
  biome at config level. AEE's biome system is runtime. **ADOPT**: the memory
  point to sound-set binding is the clean, engine-native way to attach habitat
  audio to foliage models, and it costs no script.

### 3.4 `CfgVehicles` physics keys (mass, speed, brakes, suspension, gearbox)

- **Class path**: `CfgVehicles >> <vehClass>`, and nested `complexGearbox`,
  `Wheels`, `HitPoints`.
- **What overriding changes**: `mass`, `maxSpeed`, `brakeDistance`,
  `maxBrakeTorque`, `suspensionTravel`, `wheelCircumference`, `turnCoef`,
  `terrainCoef`, `acceleration`, `thrustDelay`, `dampingRate`,
  `driveOnComponent`, `class complexGearbox { ... }`, `class Wheels { ... }`.
- **AEE status**: **partly ALREADY**. `addons/mobility/generated/CfgVehicles.hpp`
  re-declares 18 classes with `maxSpeed` and `mass` only. Each class restates
  its immediate real parent. A bare reopen is forbidden.
- **Realistic value**: `mass` is a calibrated scale of a held real mass from
  `data/physics/mass_calibration.json`; `maxSpeed` from the aircraft and
  vehicle corpora. Source: ADR-018, `docs/wiki/research/vehicle-mass-estimate.md`.
- **Ceiling**: the flight dynamics model is resolved at config load; there is
  no runtime FDM swap and no `setFlightModel` (ADR-017). The generated header
  deliberately admits no thermal key, because a redeclaration there would win
  and change the thermal model. **ALREADY** for mass and maxSpeed. **ADOPT**
  for `brakeDistance`, `maxBrakeTorque` and `complexGearbox` ratios from a
  sourced vehicle dynamics corpus. **REJECT** for a scripted aerodynamics
  replacement (renderer/solver ceiling).

### 3.5 `CfgVehicles >> DestructionEffects` (wreck and impact FX)

- **Class path**: `CfgVehicles >> <vehClass> >> class DestructionEffects`, and
  per-hitpoint `HitPoints >> <hit> >> class DestructionEffects`.
- **What overriding changes**: `simulation = "particles"`, `type` (a cloudlet),
  `position` (a named selection), `intensity`, `interval`, `lifeTime`,
  `ammoExplosionEffect`.
- **AEE status**: **not overridden**.
- **Realistic value**: the wreck cloudlet and the hit-selection come from the
  vehicle's real structure. AEE's cloudlets (`AEE_SandCloud` etc.) are the
  available `type` values.
- **Ceiling**: the effect fires on the engine's destruction event. AEE cannot
  add a new trigger, only change the particles and the selection. **ADOPT**.

### 3.6 `CfgRecoils` (weapon recoil curves)

- **Class path**: `CfgRecoils >> <recoilName>`.
- **What overriding changes**: the recoil impulse array (time, x, y, z
  sequence). Base `recoil_single_aa40` and similar.
- **AEE status**: **not overridden**. AEE computes recoil at run time
  (`addons/ballistics/functions/fnc_calculateRecoil.sqf`).
- **Realistic value**: a measured recoil impulse, derivable from projectile
  momentum and weapon mass (ADR-004, `docs/adr/ADR-004-recoil-and-item-mass.md`).
- **Ceiling**: the array is the engine's fixed-shape curve. **RECONCILE**: the
  runtime kernel is richer; a config curve is only worth it if AEE wants the
  engine to own the camera kick.

### 3.7 `CfgSurfaces` (terrain material friction and dust)

- **Class path**: `CfgSurfaces >> <surfaceClass>`; `map_data` holds the map's
  surface map.
- **What overriding changes**: friction, dust effect, sound, and the terrain
  material class. `CfgDustEffectsCar/Tank/Man/Air` select the dust cloudlet.
- **AEE status**: **not overridden**. AEE reads surface material at run time.
- **Realistic value**: soil strength and NRMM classification
  (`docs/wiki/research/soil-strength-nrmm.md`).
- **Ceiling**: the surface-to-terrain mapping is baked in the map's surface
  mask, not config. A config override reaches only the friction and dust
  parameters. **ADOPT** for friction, **REJECT** for remapping terrain (map
  data ceiling).

---

## 4. Tier 3: map, UI and presentation

### 4.1 `CfgMarkers` / `CfgMarkerClasses` / `CfgMarkerColors`

- **Class path**: `CfgMarkers >> <marker>`, `CfgMarkerClasses >> <group>`,
  `CfgMarkerColors >> <color>`.
- **What overriding changes**: `name`, `icon`, `texture`, `color[]`, `size`,
  `shadow`, `scope`, `markerClass`, `showEditorMarkerColor`.
- **AEE status**: **ALREADY**. `addons/optics/config.cpp` declares
  `AEE_Symbology`, `ColorAEE`, `AEE_MarkerBase` and the full APP-6 marker set.
  `ColorAEE` is white, so each texture shows its own colour.
- **Realistic value**: APP-6 / MIL-STD-2525. Source:
  `docs/wiki/research/nato-symbology.md`, ADR-023, ADR-024.
- **Ceiling**: the engine stretches a marker texture to the marker box and does
  not preserve aspect. A 2:1 texture needs a non-square `size` or a
  `drawIcon` width/height pair (feedback T170754, recorded in
  `the APP-6 placement research note`). **ALREADY**.

### 4.2 `CfgLocationTypes`

- **Class path**: `CfgLocationTypes >> <type>`, base in `ui_f`.
- **What overriding changes**: `font`, `color[]`, `texture`, `size`,
  `textSize`, `name`, `shadow`.
- **AEE status**: **ALREADY**. `addons/cartography/config_locationtypes.hpp`
  re-declares the name, area and vegetation symbols with FM 21-31 and USGS
  colours.
- **Realistic value**: FM 21-31 sections 9 to 21. Source:
  `docs/wiki/research/terrain-symbols.md`.
- **Ceiling**: none at config level. **ALREADY**.

### 4.3 `RscMapControl` (and the display subclasses)

- **Class path**: `RscMapControl`, `RscDisplayStrategicMap >>
  controlsBackground >> Map`, `ctrlMap` (Eden).
- **What overriding changes**: `colorLevels[]`, `colorMainCountlines[]`,
  `colorCountlines[]`, `colorRoads*`, `colorMainRoads*`, `colorRailWay`,
  `colorPowerLines`, `colorTracks*`, `colorTrails*`, `colorSea`, `colorForest`,
  `colorForestBorder`, `colorRocks`, `colorRocksBorder`, `colorBackground`,
  `colorGrid`, `colorGridMap`, `fontGrid`, `fontNames`, `sizeExGrid`,
  `maxSatelliteAlpha`, `showCountourInterval`, `ptsPerSquare*`, `alphaFade*`,
  `drawShaded`.
- **AEE status**: **ALREADY**. `addons/cartography/config_mapcolors.hpp` and
  `config_mapicons.hpp` are included inside the `RscMapControl` block.
  `config_mapdisplays.hpp` re-declares `RscDisplayStrategicMap` and `ctrlMap`.
- **Realistic value**: USGS and FM 21-31 palette. Source:
  `docs/wiki/research/map-grid-and-cursor-surface.md`.
- **Ceiling**: a display that re-declares a field wins for that display. The
  minimap overrides `maxSatelliteAlpha`, `alphaFade*`, `ptsPerSquare*`,
  `colorSea`, `colorForest` and `drawShaded`, so it keeps its own fills. Eden's
  map is `ctrlMap`, not `RscMapControl`, so an `RscMapControl` reopen does not
  reach Eden (config_mapdisplays.hpp header). **ALREADY**.

### 4.4 `CfgCurator` (Eden and Zeus symbols)

- **Class path**: `CfgCurator >> DrawGroup` and `DrawGroup >> 3D / 2D`.
- **What overriding changes**: `textureWest`, `textureEast`, `textureGuer`,
  `textureCivilian`, `textureUnknown`.
- **AEE status**: **ALREADY**. `addons/cartography/config_curator.hpp` re-declares
  the five side textures and the 3D and 2D sub-blocks.
- **Realistic value**: the real NATO affiliation frame per side. Source:
  ADR-023, `docs/wiki/research/nato-symbology.md`.
- **Ceiling**: the texture is per side, not per unit function. A specific unit
  function glyph cannot be shown here. The Eden object-tree and unit icons are
  engine-internal, like the map object-icon routing. **ALREADY**.

### 4.5 `CfgFontFamilies` (map and HUD fonts)

- **Class path**: `CfgFontFamilies >> <family>`.
- **What overriding changes**: `fonts[]` (per-size glyph files), `spaceWidth`.
- **AEE status**: **ALREADY, but inert**. `addons/optics/config.cpp` declares
  `AEEFont` and `AEEFontMono`. No `.fxy`/`.paa` glyph files ship, so the engine
  draws no text for them. The config no longer sets `fontGrid`/`fontNames`/`font`.
- **Realistic value**: a real typeface (Rajdhani, B612 Mono) rendered through
  the FontToTGA operator step. Source:
  `docs/wiki/research/arma-font-surface.md`.
- **Ceiling**: **asset-gated**. The family is inert until the glyph files
  exist. The FontToTGA step needs Windows. **RECONCILE**: keep the config, but
  the family is unusable until the glyphs ship.

### 4.6 `CfgVehicleIcons` (Eden and timeline icons)

- **Class path**: `CfgVehicleIcons >> <icon>`; base in `modules_f`,
  `functions_f`.
- **What overriding changes**: named icon path keys (`iconModule`,
  `IconTimeline`, `IconCurve`, `IconKey`, `IconControlPoint`, `IconCamera`).
- **AEE status**: **not overridden**.
- **Realistic value**: a standard icon path. Low realism value.
- **Ceiling**: the object-to-icon routing for vehicles is engine-internal, like
  the map object icons. A reopen reaches only the keys the engine already reads
  from the class. **REJECT** (low impact, engine-internal routing).

### 4.7 `CfgMovesBasic` / `CfgMovesMaleSdr` / `CfgMovesAnimal` (animation)

- **Class path**: `CfgMovesBasic`, `CfgMovesMaleSdr`, `CfgMovesAnimal`.
- **What overriding changes**: animation states, transitions, interpolation
  speeds, and the `CfgMovesAnimations` entries those classes hold.
- **AEE status**: **not overridden**. Note: the class `CfgMovesAnimations` does
  not exist in the base config. The real top-level classes are `CfgMovesBasic`,
  `CfgMovesMaleSdr` and `CfgMovesAnimal` (grep of the unpacked set).
- **Realistic value**: a sourced human locomotion model. AEE's human vision and
  physiology work is the nearest corpus (ADR-014).
- **Ceiling**: an animation override needs matching animation assets (`.rtm`
  files) and a skeleton match. A value-only reopen changes timing, not motion.
  **REJECT** unless AEE ships animations (asset-gated).

### 4.8 `CfgClothing` (AEE-authored class, not engine)

- **Class path**: `CfgClothing >> <uniformClass>`.
- **What overriding changes**: AEE's own per-uniform fields: `clo`,
  `alphaSolar`, `nirReflectance`, `permeability`, `emissivity`.
- **AEE status**: **ALREADY**. `addons/physiology/config.cpp` declares it;
  `fnc_getCamouflageProperties.sqf` reads it.
- **Realistic value**: ASHRAE 55 / ISO 11079 clo, DLA NIR reflectance,
  colour-based solar absorptivity.
- **Ceiling**: this class is not in the base game. It is an AEE convention.
  The engine ignores it. **ALREADY** (custom).

---

## 5. Priority order and the deliberate programme

The classes AEE does **not** yet override, ordered by realism return per unit
of work:

| Rank | Class | Verdict | Realism return |
|---|---|---|---|
| 1 | `CfgMagazines` | ADOPT | High. `initSpeed` and `tracersEvery` are plain scalars with cited sources. |
| 2 | `CfgAmmo` | ADOPT (reconcile with the runtime kernel) | High. Drag and tracer shape move the engine trajectory. |
| 3 | `CfgEnvSounds >> CfgEnvSpatialSounds` | ADOPT | High. Engine-native habitat audio at no script cost. |
| 4 | `CfgVehicles >> brakeDistance / maxBrakeTorque / complexGearbox` | ADOPT | High. Ground mobility realism. |
| 5 | `CfgWeapons >> dispersion / maxZeroing / recoil` | ADOPT | High. Bound to the ballistics corpus. |
| 6 | `CfgVehicles >> HitPoints >> armor` | RECONCILE | High. Scales the pool without discarding the base. |
| 7 | `CfgVehicles >> DestructionEffects` | ADOPT | Medium. Wreck and hit FX from AEE cloudlets. |
| 8 | `CfgLights` | ADOPT | Medium. Cheap, engine-native light per fire class. |
| 9 | `CfgSurfaces` (friction) | ADOPT | Medium. Soil strength corpus. |
| 10 | `CfgRecoils` | RECONCILE | Medium. Runtime kernel is richer. |
| 11 | `CfgFontFamilies` | RECONCILE | Medium, asset-gated. |
| 12 | `CfgVehicleIcons` | REJECT | Low, engine-internal. |
| 13 | `CfgMovesBasic/MaleSdr` | REJECT | Asset-gated. |

The programme: pick a domain, name the control or standard that supplies the
value, generate the override from the cited corpus, and pin it with a test.
The existing generated configs (`addons/mobility/generated/CfgVehicles.hpp`,
`addons/thermal/generated/ThermalOptics.hpp`) are the template: a generator,
a header that says "do not edit by hand", and a `--check` gate in the Makefile.

## 6. Class-name corrections

Three names in the task are not base engine classes. The real surface is named
so the programme targets a class that exists.

| Task name | Real surface | Evidence |
|---|---|---|
| `CfgBrakes` | `CfgVehicles >> brakeDistance`, `maxBrakeTorque`, `class complexGearbox` | 0 hits for `CfgBrakes` in the base set. `brakeDistance` and `maxBrakeTorque` are the real keys. |
| `CfgOpticsMode` | `CfgWeapons >> <optic> >> ItemInfo >> OpticsModes >> <mode>` | 0 hits for `CfgOpticsMode`. AEE's `ThermalOptics.hpp` confirms the real path. |
| `CfgMovesAnimations` | `CfgMovesBasic`, `CfgMovesMaleSdr`, `CfgMovesAnimal` | 0 hits for `CfgMovesAnimations`; the three real classes are present. |
| `CfgDestructionEffects` | `CfgVehicles >> <veh> >> class DestructionEffects` (nested) | No top-level class. It is nested under the vehicle and its hitpoints. |

## 7. Sources

- AEE repo: `addons/`, `docs/adr/ADR-001-engine-anchors.md`,
  `docs/adr/ADR-003-verified-ballistics-data.md`,
  `docs/adr/ADR-017-flight-physics-ceiling.md`,
  `docs/adr/ADR-018-aircraft-catalogue.md`,
  `docs/adr/ADR-019-thermal-realism.md`,
  `docs/wiki/research/{vehicle-armour-research,engine-thermal-mechanisms,
  lighting-reference-review,particle-array-spec,map-grid-and-cursor-surface,
  nato-symbology,arma-font-surface,terrain-symbols,soil-strength-nrmm,
  human-vision-model,rotor-downwash-brownout}.md`.
- AEE data: `data/ballistics/INDEX.md`, `data/physics/mass_calibration.json`,
  `data/device/catalogue/thermal_devices.json`.
- Base configs: the derapified `weapons_f` and `ui_f` configs from a full
  Arma 3 install (about 237 unpacked `config.cpp`). Extract and derapify with
  `hemtt utils pbo extract` and `hemtt utils config derapify`.
- BI Community Wiki (BIKI): `https://community.bistudio.com/wiki/` (the
  `CfgVehicles Config Reference` page returns 403 to a scripted fetch; the
  base configs are the primary source here).

Budget note: this is a forced-long report. It is about 1,600 words. The
supporting reads were 30 tool calls over the AEE repo and the base configs.
