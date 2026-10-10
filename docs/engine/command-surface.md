# Engine command surface: geometry anchors, simulation physics, event hooks, AI

This is the verified command surface for the physics-application layer. It
records the commands the ADR-001 anchor inventory, the physics-application API
and the event-hook surface depend on. It answers issue #144 and opens the
#144-#147 command-surface series.

The document names a command, its group, its introduction version and the one
caveat that changes how AEE must call it. It does not restate the area
narratives in [engine-commands-and-features.md](engine-commands-and-features.md).
Read that document for the engine systems behind the commands.

## Source and method

- **Source.** The local Arma 3 wiki command DB, acemod/arma3-wiki dist
  **v2.22**. Commands live in `commands/<name>.yml`. Event handlers live in
  `events/<category>/<name>.yml`.
- **Version.** The `since:` block of a page records the introduction version.
  The column-0 `since:` block is the command's own version. A nested,
  indented `since:` block belongs to one alternative syntax or one parameter,
  not to the command. Read the column-0 block. A command that predates the
  field carries no `arma_3` entry, shown here as **n/v** (no version
  recorded).
- **Labels.** **VERIFIED** means the value is read from the local DB page.
  **UNKNOWN** means the local DB does not carry the claim. Nothing here comes
  from memory.

The DB records no ordering field and no per-handler index. Any statement about
handler order or a handler count is marked UNKNOWN against this source.

## 1. Geometry and model commands (the ADR-001 anchors)

| Command | Since | Group | Verified spec | AEE use |
|---|---|---|---|---|
| `selectionNames` | 1.58 | Object Manipulation | Returns the named selections of the model. Default syntax reads the first LOD (index 0). The alternative syntax selects a LOD by name or resolution (that form since 2.0). | The anchor inventory (#128): per-component wheel/glass/engine mapping. |
| `selectionPosition` | 0.50 | Object Manipulation, Render Time Scope | Returns a selection position in model space, in render time scope. The default syntax searches Memory, Geometry, FireGeometry, LandContact, HitPoints, then ViewGeometry, and returns the first match. | Effect placement at component positions (#128). |
| `setObjectMaterial` | 0.50 | Object Manipulation | Sets the material of one object selection. The selection number comes from the `hiddenSelections[] = {}` array in the vehicle config, starting at 0. Since 2.20 the value `"#reset"` restores the default material. | The per-selection swap (#124, #123 fix). |
| `getObjectMaterials` | 1.38 | Object Manipulation | Gets all custom materials of the object. The array syntax returns materials in the order of the requested selections, and fills a missing material with `nil` (that form since 2.20). | Current-state read for the swap diff. |
| `modelToWorld` | 0.50 | Positions | Converts a model-space offset to world space (PositionAGL). For a scaled object the offset is multiplied by the object scale first. | Effect world placement. |
| `modelToWorldVisual` | 1.32 | Object Manipulation, Render Time Scope | As `modelToWorld`, in render time scope. It carries the same scale-multiply rule. | Frame-accurate placement for visual effects. |
| `getCenterOfMass` | 1.12 | PhysX | Returns the centre of mass of an object, as an offset relative to the model centre. | Vehicle stability (#108), physics anchor. |

**The scale caveat (VERIFIED).** `modelToWorld` and `modelToWorldVisual`
multiply the offset by the object scale. For a scale of 2, `_obj modelToWorld
[0,1,0]` is offset 2 m from the model centre. Effect placement must account
for object scale.

## 2. Simulation commands (the physics-application API)

| Command | Since | Group | Verified spec | AEE use |
|---|---|---|---|---|
| `getMass` | 1.12 | PhysX | Returns the mass of a PhysX object. | Traction, rollover, fuel, penetration. |
| `setMass` | 1.2 | PhysX | Changes the mass of a PhysX object. The alternative syntax changes the mass gradually over a given time; zero is immediate. A gradual change on a local vehicle does not run on remote clients: only the final mass arrives. | Load-state mass change (fuel burn, cargo). |
| `getCenterOfMass` | 1.12 | PhysX | See section 1. | Stability. |
| `velocityModelSpace` | 0.50 | Object Manipulation | Returns the velocity vector in model space, in m/s. | Local-wind interaction, hydroplaning. |
| `setVelocityModelSpace` | 1.68 | Object Manipulation | Sets the velocity vector relative to the model. Since 2.06 each component is limited to ±5000 m/s. | Local-wind interaction. |
| `setVelocity` | 0.50 | Object Manipulation | Sets the velocity vector in m/s. Since 2.06 each component is limited to ±5000 m/s. | Hydroplaning, black-ice traction response. |
| `setDamage` | 0.50 | Object Manipulation | Sets the damage of an object or unit. The alternative syntax skips destruction effects for vehicles. | Damage-state write. |
| `damage` | 0.50 | Object Manipulation | Returns the damage value, in the range 0 (healthy) to 1 (dead). Alias `getDammage`. | Damage-state read for thermal and armour. |
| `setFuel` | 0.50 | Object Manipulation | Sets the fuel level. | Fuel model (#111) write. |
| `fuel` | 0.50 | Object Manipulation | Returns the fuel level, 0 (empty) to 1 (full). | Fuel model read. |
| `getFuelCargo` | 0.56 | Vehicle Inventory | Returns the fuel cargo of a vehicle. | Vehicle fuel cargo. |
| `engineOn` | 0.50 | Object Manipulation | Turns the vehicle engine on or off. On a remote vehicle the engine may turn on and then turn off by itself after a short time. | Thermal engine state, acoustic signature. |
| `simulationEnabled` | 0.50 | Object Manipulation | Reports whether the entity has simulation enabled. The result is the state set up locally on the client that ran the command. | Performance culling (#97). |

## 3. Event scripting (the hook surface)

### addEventHandler

`addEventHandler` is **VERIFIED** at 0.50, group Event Handlers. It takes
`[type, code]` and returns the handler index (indices start at 0 and increase
per object). Several handlers of one type stack: a later handler does not
overwrite an earlier one. Remove a handler with `removeEventHandler`. Some
handlers are persistent and stay attached after death and respawn.

The issue states the code runs "in missionNamespace by default" with "Magic
Variables". The local DB page does **not** carry that wording: it defers to
the Event Handlers category. The parameter delivery is defined per handler, in
each handler page's `params` list. Treat the magic-variable phrasing as
**UNKNOWN** against the local DB.

### The named object handlers

Each row is VERIFIED against `events/standard/<name>.yml`. **n/v** is "no
Arma 3 version recorded".

| Handler | Since | Verified role | AEE use |
|---|---|---|---|
| `HitPart` | n/v | Runs when the object is injured or damaged. Delivers a nested array, one sub-array per hit part: target, shooter, projectile, position, velocity, selection, ammo, vector, radius, surface, direct, instigator. Fires only on the shooter's PC. Does not fire on fall damage or burning. | Ballistic impact hook (armour #126, fragmentation #107, blast #132). |
| `Explosion` | 0.76 | Fires when a vehicle or unit is damaged by a nearby explosion. Delivers vehicle, damage, source. Fires even for tiny explosion damage that `HitPart` ignores. | Explosion hook (blast, craters #19). |
| `Fired` | n/v | Fires when the unit fires a weapon. Does not fire when a unit fires from a vehicle. | Weapon fire (barrel heat #130, sound #80, AI hearing #74). |
| `FiredMan` | 1.66 | The unit-fired variant. | Weapon fire. |
| `FiredNear` | n/v | Fires when a weapon fires near the unit. | Weapon fire. |
| `Dammaged` | n/v | Fires when the object damage changes. | Damage-state change (thermal from damage). |
| `Engine` | n/v | Fires when the engine turns on or off. Global, but on a client it fires for a remote vehicle only within about 6 km of the camera. | Acoustic signature, thermal. |
| `Fuel` | n/v | Fires when the fuel level changes. | Fuel model. |
| `GetIn` | n/v | Fires when a unit gets into a vehicle. | Crew state. |
| `GetOut` | n/v | Fires when a unit gets out of a vehicle. | Crew state. |
| `GetInMan` | 1.58 | The unit variant of `GetIn`. | Crew state. |
| `GetOutMan` | 1.58 | The unit variant of `GetOut`. | Crew state. |
| `HandleDamage` | n/v | Fires for each damaged selection when the unit is damaged, and only on the PC where the unit is local. A returned number overrides the default damage for that selection. Only the last added handler's return value counts. | Damage override point (#126 guard). |
| `Hit` | n/v | Fires when the unit is hit or damaged. Does not always fire on a kill, and does not fire when `allowDamage` is false. | Per-hit damage. |
| `Killed` | n/v | Fires when the unit is killed. | Death handling. |
| `SeatSwitched` | 1.50 | Fires when a unit switches seat. | Crew state. |
| `SeatSwitchedMan` | 1.58 | The unit variant of `SeatSwitched`. | Crew state. |
| `VisionModeChanged` | 2.8 | Fires when the vision mode changes. | Optics. |
| `WeaponChanged` | 2.18 | Fires when the weapon changes. | Weapon state. |
| `Suppressed` | 2.2 | Fires when an enemy projectile passes closer than the suppression radius in the ammo config. Delivers unit, distance, shooter, instigator, ammo object, ammo class name. | Suppression psychology (#110). |
| `IncomingMissile` | n/v | Fires when a unit fires a missile or rocket at the target. For a player-fired projectile it fires only for a guided missile that has locked on. | Missile warning (#131). |
| `SoundPlayed` | 0.56 | Fires when the player makes an injury or fatigue noise. The number parameter points to the sound origin (breath, injured, pulsation, hit scream, and so on). | Sound hook. |

### The handler surface beyond the named set

The DB splits handlers by the object they attach to:

| Category | Path | Pages |
|---|---|---|
| Object/entity | `events/standard/` minus Curator and 3DEN pages | 79 |
| Mission | `events/mission/` | 54 |
| Group | `events/group/` | 20 |
| Projectile | `events/projectile/` | 10 |
| Eden editor | `events/eden/` | 59 |
| User interface | `events/user_interface/` | 53 |
| Multiplayer | `events/multiplayer/` | 4 |
| Music | `events/music/` | 2 |
| User action | `events/user_action/` | 3 |

`events/standard/` holds 107 pages. Of these, 23 are `Curator*` (Eden curator)
and 5 are 3DEN (`AttributesChanged3DEN`, `ConnectionChanged3DEN`,
`Dragged3DEN`, `RegisteredToWorld3DEN`, `UnregisteredFromWorld3DEN`). The
remainder, 79, are the object/entity handlers.

**UNKNOWN against the local DB.** The issue's "80 object event handlers" and
its per-handler order numbers (`HitPart` #38, `Explosion` #20, `Fired` #21-23,
and so on). The DB records no order field and no partition that equals 80.
The exact published ordering is not reproducible from the local DB.

### The projectile handlers

The projectile hooks are separate from the entity hooks. `events/projectile/`
holds 10 handlers: `Analog`, `Deflected`, `Deleted`, `Explode`, `HitExplosion`,
`HitPart`, `Init`, `MineActivated` (2.14), `Penetrated`, `SubmunitionCreated`.
The projectile `HitPart` delivers projectile, hitEntity, projectileOwner, pos,
velocity, normal, components, radius, surfaceType, instigator. It fires on a
direct hit only, not on splash damage. Use `HitExplosion` for splash damage.

## 4. AI commands (the AI surface, from #74, #75, #81)

| Command | Since | Group | Verified spec | AEE use |
|---|---|---|---|---|
| `reveal` | 0.50 | Object Manipulation | Reveals a target to a group. Sets the knowledge value to the highest level any unit of the revealing side has; if the side has no knowledge, the value is 1. **The knowledge level can only be increased, never decreased. Use `forgetTarget` first to decrease it.** Local: `targetKnowledge` and `knowsAbout` update only on the PC that ran the command. | Sound to hearing (#74). The monotonic rule matters: the AI hearing model must call `forgetTarget` before lowering a unit's knowledge, or a scaled hearing value never reduces. |
| `setSuppression` | 1.42 | Object Manipulation | Sets the suppression value of a unit. Local. | Suppression psychology (#110), rain and wind stress. |
| `suppressFor` | 0.50 | Unit Control | Forces suppressive fire from the unit for a given duration. | AI response. |
| `selectBestPlaces` | 0.50 | Mission Information | Finds the places with the maximum value of an expression in an area. Takes position, radius, expression, precision, sourcesCount. The search pattern is randomised on each call. The example uses `"meadow + 2*hills"`. | AI pathfinding (#81). |

**UNKNOWN against the local DB.** The issue lists the `selectBestPlaces`
expression variables as `forest trees meadow hills houses sea coast night rain
windy deadBody waterDepth camDepth`. The DB page carries no such variable
list; only `meadow` and `hills` appear, in the example. Treat the full list as
UNKNOWN.

## 5. Corrections against issue #144

Two command names in the issue do not exist in the DB:

1. **`getVelocityModelSpace` does not exist.** The getter is
   `velocityModelSpace` (0.50). The setter is `setVelocityModelSpace` (1.68).
   The ±5000 m/s limit (since 2.06) applies to the setters.
2. **`getDamage` does not exist.** The getter is `damage` (0.50), alias
   `getDammage`. The setter is `setDamage` (0.50).

The following issue claims are UNKNOWN against the local DB: the "80 object
event handlers" count and the per-handler order numbers; the `addEventHandler`
"missionNamespace / Magic Variables" wording; the full `selectBestPlaces`
expression-variable list.

## Sources

- Command DB: acemod/arma3-wiki dist v2.22. Commands read from
  `commands/<name>.yml`: `selectionNames`, `selectionPosition`,
  `setObjectMaterial`, `getObjectMaterials`, `modelToWorld`,
  `modelToWorldVisual`, `getCenterOfMass`, `getMass`, `setMass`,
  `velocityModelSpace`, `setVelocityModelSpace`, `setVelocity`, `setDamage`,
  `damage`, `setFuel`, `fuel`, `getFuelCargo`, `engineOn`,
  `simulationEnabled`, `reveal`, `setSuppression`, `suppressFor`,
  `selectBestPlaces`, `addEventHandler`.
- Event handlers: acemod/arma3-wiki dist v2.22, `events/standard/<name>.yml`
  and `events/projectile/<name>.yml`. Pages used: `HitPart`, `Explosion`,
  `Fired`, `FiredMan`, `FiredNear`, `Dammaged`, `Engine`, `Fuel`, `GetIn`,
  `GetOut`, `GetInMan`, `GetOutMan`, `HandleDamage`, `Hit`, `Killed`,
  `SeatSwitched`, `SeatSwitchedMan`, `VisionModeChanged`, `WeaponChanged`,
  `Suppressed`, `IncomingMissile`, `SoundPlayed`.
- Related AEE records: `docs/adr/ADR-001-engine-anchors.md`,
  `docs/adr/ADR-037-physx-mass-surface-and-the-grade-gate.md`,
  [engine-config-surface.md](engine-config-surface.md),
  [engine-commands-and-features.md](engine-commands-and-features.md).
