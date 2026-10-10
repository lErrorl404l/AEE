# Arma 3 engine command inventory: the complete group surface

Purpose: the complete Arma 3 scripting command surface, grouped, so AEE can
find a command and know its group and its introduction version. This is the
capstone of the command-surface series (#141, #144, #145, #146). It is the
master index. The sibling maps give the per-command semantics for the
AEE-relevant groups. This document does not repeat them.

## 1. Source and method

- **Source.** The local Arma 3 wiki command DB, acemod/arma3-wiki dist
  **v2.22**. Each command is one page, `commands/<name>.yml`.
- **Count.** The DB holds 2696 command pages. 2653 carry an Arma 3 version.
- **Version.** The column-0 `since:` block records the introduction version.
  A nested, indented `since:` block belongs to one syntax alternative or one
  parameter, never to the command. Read the column-0 block. A command that
  predates the field carries no Arma 3 entry, shown here as **n/v** (no
  version recorded).
- **Labels.** **VERIFIED** means the value is read from the local DB page.
  **UNKNOWN** means the local DB does not carry the claim. Nothing here comes
  from memory.

The DB assigns each command one or more group labels. A command can carry two
labels, so the group counts below sum to more than the page count.

## 2. The group surface and the "74" claim

The issue names 74 command groups. The local DB carries **89 group labels**.
The difference is the DB keeps sub-groups separate: GUI Control has 10
sub-groups (ListBox, ListNBox, Tree View, Positioning, Menu, Map, HTML,
Controls Table, Event Handlers, Object), Math has 2 (Vectors, Geometry) and
Strings has 1 (Regular Expression). Those 13 sub-groups do not reconcile the
74 exactly. The local DB carries no group-count field, so the exact 74-group
list is **UNKNOWN** against this source. The 89 labels below are the verified
ground truth.

Every group label, its command count and its Arma 3 version range:

| Group | Commands | Arma 3 version | Detail |
|---|---:|---|---|
| Object Manipulation | 264 | 0.50 to 2.22 | [#144] |
| Unit Inventory | 127 | 0.50 to 2.22 | this document, §4 |
| GUI Control | 126 | 0.50 to 2.24 | [#146] |
| System | 88 | 0.50 to 2.20 | [#145] |
| Unit Control | 81 | 0.50 to 2.18 | this document, §4 |
| Multiplayer | 79 | 0.50 to 2.20 | this document, §4 |
| Camera Control | 68 | 0.50 to 2.22 | [#146] |
| Interaction | 67 | 0.50 to 2.22 | this document, §4 |
| Environment | 66 | 0.50 to 2.10 | [#141] |
| Briefing | 63 | 0.50 to 2.10 | this document, §4 |
| Sounds | 63 | 0.50 to 2.18 | [#146] |
| Waypoints | 63 | 0.50 to 2.00 | this document, §4 |
| Variables | 62 | 0.50 to 2.18 | this document, §4 |
| Game 2 Editor | 57 | 0.50 | this document, §4 |
| Eden Editor | 56 | 1.56 to 2.18 | [#146] |
| Weapons | 53 | 0.50 to 2.22 | this document, §4 |
| Positions | 52 | 0.50 to 2.18 | this document, §4 |
| Diagnostic | 50 | 0.50 to 2.18 | [#145] |
| Groups | 50 | 0.50 to 2.14 | this document, §4 |
| Markers | 49 | 0.50 to 2.14 | this document, §4 |
| Program Flow | 49 | 0.50 to 2.14 | this document, §4 |
| Containers | 48 | 0.50 to 1.22 | this document, §4 |
| Event Handlers | 48 | 0.50 to 2.10 | [#144] |
| RTD | 46 | 1.34 | this document, §4 |
| Curator | 44 | 1.16 to 2.14 | [#146] |
| Strings | 43 | 0.50 to 2.18 | this document, §4 |
| Object Detection | 42 | 0.50 to 2.18 | this document, §4 |
| Mission Information | 41 | 0.50 to 2.20 | this document, §4 |
| Radio and Chat | 41 | 0.50 to 2.06 | this document, §4 |
| GUI Control - ListBox | 40 | 0.50 to 2.06 | [#146] |
| Math | 40 | 0.50 to 1.92 | this document, §4 |
| GUI Control - ListNBox | 38 | 0.50 to 2.06 | [#146] |
| Sides | 38 | 0.50 to 1.58 | this document, §4 |
| Vehicle Inventory | 38 | 0.50 to 1.94 | this document, §4 |
| GUI Control - Tree View | 37 | 0.74 to 2.02 | [#146] |
| Arrays | 36 | 0.50 to 2.14 | this document, §4 |
| Broken Commands | 36 | 0.50 to 1.56 | this document, §4 |
| Turrets | 34 | 0.50 to 2.22 | this document, §4 |
| Triggers | 33 | 0.50 to 2.14 | this document, §4 |
| Locations | 31 | 0.50 to 2.14 | this document, §4 |
| Lights | 30 | 0.50 to 2.08 | [#141/#146] |
| Animations | 28 | 0.50 to 2.18 | this document, §4 |
| Config | 28 | 0.50 to 2.10 | this document, §4 |
| GUI Control - Positioning | 28 | 0.50 to 2.02 | [#146] |
| Math - Vectors | 28 | 0.50 to 2.14 | this document, §4 |
| GUI Control - Menu | 27 | 1.56 to 2.02 | [#146] |
| High Command | 27 | 0.50 | this document, §4 |
| Math - Geometry | 24 | 0.50 to 1.68 | this document, §4 |
| GUI Control - Map | 23 | 0.50 to 2.20 | [#146] |
| Ropes and Sling Loading | 23 | 1.34 to 2.12 | this document, §4 |
| AI Behaviour | 22 | 0.50 to 2.18 | [#144] |
| GUI Control - HTML | 22 | 0.50 | [#146] |
| Teams | 22 | 0.50 | this document, §4 |
| PhysX | 21 | 1.02 to 2.22 | [#144] |
| Remote Control | 21 | 0.50 to 2.16 | this document, §4 |
| Stamina System | 21 | 0.50 to 1.62 | this document, §4 |
| Unit Identity | 20 | 0.50 to 2.18 | this document, §4 |
| GUI Control - Controls Table | 19 | 1.70 | [#146] |
| HashMap | 19 | 0.50 to 2.14 | this document, §4 |
| Sensors | 19 | 1.52 to 2.22 | this document, §4 |
| Argo | 18 | n/v | this document, §4 |
| Render Time Scope | 18 | 0.50 to 2.22 | [#146] |
| Namespaces | 16 | 0.50 to 2.10 | this document, §4 |
| Time | 15 | 0.50 to 2.20 | this document, §4 |
| Map | 14 | 0.50 to 2.10 | this document, §4 |
| Weapon Pool | 14 | 0.50 to 1.12 | this document, §4 |
| Dynamic Simulation | 12 | 1.68 | this document, §4 |
| DLC | 11 | 1.00 to 2.00 | this document, §4 |
| Difficulty | 11 | 0.50 to 2.02 | this document, §4 |
| Flags | 11 | 0.50 to 1.70 | this document, §4 |
| Mods and Addons | 11 | 0.50 to 2.00 | this document, §4 |
| Structured Text | 11 | 0.50 | this document, §4 |
| Mines | 10 | 0.50 to 1.62 | this document, §4 |
| Pilot Camera | 10 | 1.64 to 2.14 | [#146] |
| Roads and Airports | 10 | 0.50 to 2.00 | this document, §4 |
| GUI Control - Event Handlers | 9 | 0.50 | [#146] |
| GUI Control - Object | 9 | 1.32 to 2.18 | [#146] |
| Leaderboards | 9 | 1.42 to 1.56 | this document, §4 |
| Performance Profiling | 9 | 0.50 to 2.16 | this document, §4 |
| Vehicle Loadouts | 9 | 1.70 to 2.02 | this document, §4 |
| Artillery | 8 | 0.50 to 0.56 | this document, §4 |
| Conversations | 8 | 0.50 | this document, §4 |
| Custom Panels | 8 | 1.16 to 1.72 | this document, §4 |
| Custom Radio and Chat | 8 | 0.50 to 2.00 | this document, §4 |
| Particles | 8 | 0.50 to 1.08 | [#146] |
| Team Switch | 8 | 0.50 | this document, §4 |
| Vehicle in Vehicle Transport | 6 | 1.62 | this document, §4 |
| Localization | 5 | 0.50 to 2.04 | this document, §4 |
| Strings - Regular Expression | 3 | 2.06 | this document, §4 |

## 3. The AEE-relevant groups (detailed in the sibling maps)

These groups drive AEE. Each is mapped per command in its sibling document.
Read the sibling for the semantics and the caveats. This section gives the
group, its count and a few key commands with their verified version.

| Group | Commands | Key commands (since) | Detail |
|---|---:|---|---|
| Environment | 66 | `date` (0.50), `dayTime` (0.50), `timeMultiplier` (1.26), `setOvercast` (0.50), `setRain` (0.50), `fog` (0.50) | #141 |
| Object Manipulation | 264 | `selectionNames` (1.58), `selectionPosition` (0.50), `setObjectMaterial` (0.50), `modelToWorld` (0.50), `setVelocity` (0.50), `setDamage` (0.50), `damage` (0.50), `setFuel` (0.50), `fuel` (0.50), `engineOn` (0.50) | #144 |
| PhysX | 21 | `getMass` (1.12), `setMass` (1.2), `getCenterOfMass` (1.12) | #144 |
| Event Handlers | 48 | `addEventHandler` (0.50), `removeEventHandler` (0.50), `removeAllEventHandlers` (0.50) | #144 |
| AI Behaviour | 22 | `setUnitAbility` (0.50), `setCombatMode` (0.50), `combatMode` (0.50) | #144 |
| System | 88 | `isDedicated` (0.50), `isServer` (0.50), `isMultiplayer` (0.50), `serverTime` (0.50) | #145 |
| Diagnostic | 50 | `diag_tickTime` (0.50), `diag_frameNo` (0.50), `diag_fps` (0.50), `diag_log` (0.50) | #145 |
| Sounds | 63 | `createSoundSource` (0.50), `playSound3D` (0.50), `say3D` (0.50) | #146 |
| Particles | 8 | `setParticleParams` (0.50), `setParticleRandom` (0.50), `setParticleCircle` (0.50) | #146 |
| Camera Control | 68 | `ppEffectCreate` (0.50), `ppEffectAdjust` (0.50), `camCreate` (0.50), `cameraEffect` (0.50), `camSetPos` (0.50) | #146 |
| GUI Control | 126 | `createDialog` (0.50), `createDisplay` (0.50), `ctrlCreate` (1.26), `ctrlSetText` (0.50) | #146 |
| GUI Control - Controls Table | 19 | - | #146 |
| GUI Control - Event Handlers | 9 | - | #146 |
| GUI Control - HTML | 22 | - | #146 |
| GUI Control - ListBox | 40 | - | #146 |
| GUI Control - ListNBox | 38 | - | #146 |
| GUI Control - Map | 23 | `drawLine` (0.50), `drawIcon` (0.50), `ctrlMapScreenToWorld` (0.50) | #146 |
| GUI Control - Menu | 27 | - | #146 |
| GUI Control - Object | 9 | - | #146 |
| GUI Control - Positioning | 28 | - | #146 |
| GUI Control - Tree View | 37 | - | #146 |
| Eden Editor | 56 | `get3DENSelected` (1.56), `set3DENAttribute` (1.56), `add3DENConnection` (1.56) | #146 |
| Curator | 44 | `addCuratorEditableObjects` (1.16), `curatorEditableObjects` (1.16), `curatorSelected` (1.16) | #146 |
| Lights | 30 | `setLightColor` (0.50), `setLightBrightness` (0.50), `setLightIntensity` (0.50), `lightAttachObject` (0.50) | #141/#146 |
| Render Time Scope | 18 | `selectionPosition` (0.50), `modelToWorldVisual` (1.32) | #146 |
| Pilot Camera | 10 | `setPilotCameraTarget` (1.64), `hasPilotCamera` (1.64) | #146 |

## 4. The complete inventory of the remaining groups

Each group below lists every command it holds, with its introduction
version. These groups are not detailed in a sibling map. The list is the
complete membership of the group in the local DB.

### Physics and simulation

#### Artillery (8 commands, since 0.50 to 0.56)

| Command | Since |
|---|---|
| `commandArtilleryFire` | 0.50 |
| `doArtilleryFire` | 0.50 |
| `enableEngineArtillery` | 0.50 |
| `getArtilleryAmmo` | 0.50 |
| `getArtilleryComputerSettings` | 0.50 |
| `inRangeOfArtillery` | 0.50 |
| `shownArtilleryComputer` | 0.50 |
| `getArtilleryETA` | 0.56 |

#### Dynamic Simulation (12 commands, since 1.68)

| Command | Since |
|---|---|
| `canTriggerDynamicSimulation` | 1.68 |
| `diag_dynamicSimulationEnd` | 1.68 |
| `diag_dynamicSimulationStart` | 1.68 |
| `dynamicSimulationDistance` | 1.68 |
| `dynamicSimulationDistanceCoef` | 1.68 |
| `dynamicSimulationEnabled` | 1.68 |
| `dynamicSimulationSystemEnabled` | 1.68 |
| `enableDynamicSimulation` | 1.68 |
| `enableDynamicSimulationSystem` | 1.68 |
| `setDynamicSimulationDistance` | 1.68 |
| `setDynamicSimulationDistanceCoef` | 1.68 |
| `triggerDynamicSimulation` | 1.68 |

#### Mines (10 commands, since 0.50 to 1.62)

| Command | Since |
|---|---|
| `createMine` | 0.50 |
| `mineActive` | 0.50 |
| `revealMine` | 0.50 |
| `allMines` | 1.24 |
| `detectedMines` | 1.24 |
| `mineDetectedBy` | 1.24 |
| `addOwnedMine` | 1.62 |
| `getAllOwnedMines` | 1.62 |
| `removeAllOwnedMines` | 1.62 |
| `removeOwnedMine` | 1.62 |

#### Ropes and Sling Loading (23 commands, since 1.34 to 2.12)

| Command | Since |
|---|---|
| `canSlingLoad` | 1.34 |
| `enableRopeAttach` | 1.34 |
| `getSlingLoad` | 1.34 |
| `ropeAttachEnabled` | 1.34 |
| `ropeAttachTo` | 1.34 |
| `ropeAttachedObjects` | 1.34 |
| `ropeAttachedTo` | 1.34 |
| `ropeCreate` | 1.34 |
| `ropeCut` | 1.34 |
| `ropeDestroy` | 1.34 |
| `ropeDetach` | 1.34 |
| `ropeEndPosition` | 1.34 |
| `ropeLength` | 1.34 |
| `ropeUnwind` | 1.34 |
| `ropeUnwound` | 1.34 |
| `ropes` | 1.34 |
| `setSlingLoad` | 1.34 |
| `slingLoadAssistantShown` | 1.34 |
| `ropeSegments` | 2.4 |
| `setTowParent` | 2.6 |
| `ropesAttachedTo` | 2.10 |
| `getTowParent` | 2.12 |
| `ropeSetCargoMass` | n/v |

#### Turrets (34 commands, since 0.50 to 2.22)

| Command | Since |
|---|---|
| `addMagazineTurret` | 0.50 |
| `assignAsTurret` | 0.50 |
| `loadMagazine` | 0.50 |
| `lockTurret` | 0.50 |
| `lockedTurret` | 0.50 |
| `magazinesTurret` | 0.50 |
| `moveInTurret` | 0.50 |
| `removeMagazineTurret` | 0.50 |
| `removeMagazinesTurret` | 0.50 |
| `turretUnit` | 0.50 |
| `weaponsTurret` | 0.50 |
| `currentMagazineDetailTurret` | 1.12 |
| `currentMagazineTurret` | 1.12 |
| `currentWeaponTurret` | 1.12 |
| `selectWeaponTurret` | 1.12 |
| `addWeaponTurret` | 1.32 |
| `removeWeaponTurret` | 1.32 |
| `turretLocal` | 1.32 |
| `allTurrets` | 1.34 |
| `enablePersonTurret` | 1.34 |
| `magazineTurretAmmo` | 1.34 |
| `setMagazineTurretAmmo` | 1.34 |
| `turretOwner` | 1.38 |
| `magazinesAllTurrets` | 1.52 |
| `unitTurret` | 2.0 |
| `directionStabilizationEnabled` | 2.6 |
| `enableDirectionStabilization` | 2.6 |
| `getTurretOpticsMode` | 2.10 |
| `setTurretOpticsMode` | 2.10 |
| `getTurretLimits` | 2.12 |
| `setTurretLimits` | 2.12 |
| `addMagazinesTurret` | 2.20 |
| `removeAllMagazinesTurret` | 2.20 |
| `enableGunStabilization` | 2.22 |

#### Weapons (53 commands, since 0.50 to 2.22)

| Command | Since |
|---|---|
| `aimedAtTarget` | 0.50 |
| `canFire` | 0.50 |
| `currentMuzzle` | 0.50 |
| `currentVisionMode` | 0.50 |
| `currentWeapon` | 0.50 |
| `currentWeaponMode` | 0.50 |
| `currentZeroing` | 0.50 |
| `disableTIEquipment` | 0.50 |
| `enableGunLights` | 0.50 |
| `enableIRLasers` | 0.50 |
| `enableReload` | 0.50 |
| `fire` | 0.50 |
| `fireAtTarget` | 0.50 |
| `forceWeaponFire` | 0.50 |
| `hasWeapon` | 0.50 |
| `isFlashlightOn` | 0.50 |
| `isManualFire` | 0.50 |
| `laserTarget` | 0.50 |
| `loadMagazine` | 0.50 |
| `needReload` | 0.50 |
| `reload` | 0.50 |
| `reloadEnabled` | 0.50 |
| `selectWeapon` | 0.50 |
| `setWeaponReloadingTime` | 0.50 |
| `weaponDirection` | 0.50 |
| `weaponLowered` | 0.50 |
| `weaponState` | 0.50 |
| `isWeaponDeployed` | 1.42 |
| `isWeaponRested` | 1.42 |
| `currentThrowable` | 1.48 |
| `weaponInertia` | 1.48 |
| `disableNVGEquipment` | 1.52 |
| `getShotParents` | 1.62 |
| `getWeaponSway` | 1.62 |
| `setShotParents` | 1.66 |
| `enableWeaponDisassembly` | 1.68 |
| `isLaserOn` | 1.78 |
| `missileTarget` | 1.92 |
| `missileTargetPos` | 1.92 |
| `setMissileTarget` | 1.92 |
| `setMissileTargetPos` | 1.92 |
| `setWeaponZeroing` | 2.4 |
| `canDeployWeapon` | 2.6 |
| `weaponReloadingTime` | 2.6 |
| `compatibleItems` | 2.10 |
| `compatibleMagazines` | 2.10 |
| `weaponsInfo` | 2.10 |
| `weaponDisassemblyEnabled` | 2.14 |
| `isThrowable` | 2.18 |
| `missileState` | 2.18 |
| `selectThrowable` | 2.18 |
| `throwables` | 2.18 |
| `compatibleWeapons` | 2.22 |

#### Weapon Pool (14 commands, since 0.50 to 1.12)

| Command | Since |
|---|---|
| `addMagazinePool` | 0.50 |
| `addWeaponPool` | 0.50 |
| `clearMagazinePool` | 0.50 |
| `clearWeaponPool` | 0.50 |
| `fillWeaponsFromPool` | 0.50 |
| `loadStatus` | 0.50 |
| `pickWeaponPool` | 0.50 |
| `putWeaponPool` | 0.50 |
| `queryMagazinePool` | 0.50 |
| `queryWeaponPool` | 0.50 |
| `saveStatus` | 0.50 |
| `clearItemPool` | 1.0 |
| `addItemPool` | 1.4 |
| `queryItemsPool` | 1.12 |

#### Vehicle Loadouts (9 commands, since 1.70 to 2.02)

| Command | Since |
|---|---|
| `ammoOnPylon` | 1.70 |
| `animateBay` | 1.70 |
| `animatePylon` | 1.70 |
| `getPylonMagazines` | 1.70 |
| `setAmmoOnPylon` | 1.70 |
| `setPylonLoadout` | 1.70 |
| `setPylonsPriority` | 1.70 |
| `getCompatiblePylonMagazines` | 1.72 |
| `getAllPylonsInfo` | 2.2 |

#### Vehicle Inventory (38 commands, since 0.50 to 1.94)

| Command | Since |
|---|---|
| `addItemCargo` | 0.50 |
| `addItemCargoGlobal` | 0.50 |
| `addWeapon` | 0.50 |
| `currentMagazine` | 0.50 |
| `currentMagazineDetail` | 0.50 |
| `getItemCargo` | 0.50 |
| `getMagazineCargo` | 0.50 |
| `getWeaponCargo` | 0.50 |
| `itemCargo` | 0.50 |
| `magazineCargo` | 0.50 |
| `magazines` | 0.50 |
| `magazinesDetail` | 0.50 |
| `removeWeapon` | 0.50 |
| `setAmmo` | 0.50 |
| `setAmmoCargo` | 0.50 |
| `setFuelCargo` | 0.50 |
| `setRepairCargo` | 0.50 |
| `setVehicleAmmo` | 0.50 |
| `setVehicleAmmoDef` | 0.50 |
| `weaponCargo` | 0.50 |
| `weapons` | 0.50 |
| `getAmmoCargo` | 0.56 |
| `getFuelCargo` | 0.56 |
| `getRepairCargo` | 0.56 |
| `addWeaponGlobal` | 0.76 |
| `magazinesAmmo` | 0.76 |
| `magazinesAmmoFull` | 0.76 |
| `removeWeaponGlobal` | 0.76 |
| `weaponsItems` | 0.76 |
| `everyContainer` | 1.22 |
| `magazinesAmmoCargo` | 1.22 |
| `removeWeaponAttachmentCargo` | 1.22 |
| `removeWeaponCargo` | 1.22 |
| `weaponAccessoriesCargo` | 1.22 |
| `weaponsItemsCargo` | 1.22 |
| `addMagazineAmmoCargo` | 1.32 |
| `addWeaponWithAttachmentsCargo` | 1.94 |
| `addWeaponWithAttachmentsCargoGlobal` | 1.94 |

#### Unit Inventory (127 commands, since 0.50 to 2.22)

| Command | Since |
|---|---|
| `addGoggles` | 0.50 |
| `addHandgunItem` | 0.50 |
| `addHeadgear` | 0.50 |
| `addItem` | 0.50 |
| `addMagazine` | 0.50 |
| `addMagazines` | 0.50 |
| `addPrimaryWeaponItem` | 0.50 |
| `addSecondaryWeaponItem` | 0.50 |
| `addUniform` | 0.50 |
| `addVest` | 0.50 |
| `addWeapon` | 0.50 |
| `ammo` | 0.50 |
| `assignItem` | 0.50 |
| `assignedItems` | 0.50 |
| `backpackMagazines` | 0.50 |
| `currentMagazine` | 0.50 |
| `currentMagazineDetail` | 0.50 |
| `currentWeapon` | 0.50 |
| `gearIDCAmmoCount` | 0.50 |
| `gearSlotAmmoCount` | 0.50 |
| `gearSlotData` | 0.50 |
| `goggles` | 0.50 |
| `handgunItems` | 0.50 |
| `handgunWeapon` | 0.50 |
| `hasWeapon` | 0.50 |
| `headgear` | 0.50 |
| `items` | 0.50 |
| `linkItem` | 0.50 |
| `load` | 0.50 |
| `loadAbs` | 0.50 |
| `loadUniform` | 0.50 |
| `loadVest` | 0.50 |
| `magazines` | 0.50 |
| `magazinesDetail` | 0.50 |
| `primaryWeapon` | 0.50 |
| `primaryWeaponItems` | 0.50 |
| `removeAllAssignedItems` | 0.50 |
| `removeAllContainers` | 0.50 |
| `removeAllItems` | 0.50 |
| `removeAllWeapons` | 0.50 |
| `removeGoggles` | 0.50 |
| `removeHeadgear` | 0.50 |
| `removeItem` | 0.50 |
| `removeItems` | 0.50 |
| `removeMagazine` | 0.50 |
| `removeMagazines` | 0.50 |
| `removeUniform` | 0.50 |
| `removeVest` | 0.50 |
| `removeWeapon` | 0.50 |
| `secondaryWeapon` | 0.50 |
| `secondaryWeaponItems` | 0.50 |
| `setAmmo` | 0.50 |
| `setVehicleAmmoDef` | 0.50 |
| `soldierMagazines` | 0.50 |
| `someAmmo` | 0.50 |
| `unassignItem` | 0.50 |
| `uniform` | 0.50 |
| `uniformItems` | 0.50 |
| `uniformMagazines` | 0.50 |
| `vest` | 0.50 |
| `vestItems` | 0.50 |
| `vestMagazines` | 0.50 |
| `weaponAccessories` | 0.50 |
| `weaponCargo` | 0.50 |
| `weapons` | 0.50 |
| `canAdd` | 0.70 |
| `handgunMagazine` | 0.70 |
| `primaryWeaponMagazine` | 0.70 |
| `removeAllHandgunItems` | 0.70 |
| `removeAllPrimaryWeaponItems` | 0.70 |
| `removeHandgunItem` | 0.70 |
| `removePrimaryWeaponItem` | 0.70 |
| `secondaryWeaponMagazine` | 0.70 |
| `addMagazineGlobal` | 0.76 |
| `addWeaponGlobal` | 0.76 |
| `magazinesAmmo` | 0.76 |
| `magazinesAmmoFull` | 0.76 |
| `removeMagazineGlobal` | 0.76 |
| `removeWeaponGlobal` | 0.76 |
| `weaponsItems` | 0.76 |
| `unlinkItem` | 1.0 |
| `addItemToUniform` | 1.4 |
| `addItemToVest` | 1.4 |
| `canAddItemToUniform` | 1.4 |
| `canAddItemToVest` | 1.4 |
| `itemsWithMagazines` | 1.4 |
| `magazinesDetailBackpack` | 1.4 |
| `magazinesDetailUniform` | 1.4 |
| `magazinesDetailVest` | 1.4 |
| `removeAllItemsWithMagazines` | 1.4 |
| `uniformContainer` | 1.4 |
| `vestContainer` | 1.4 |
| `binocular` | 1.12 |
| `hmd` | 1.12 |
| `forceAddUniform` | 1.22 |
| `isUniformAllowed` | 1.22 |
| `weaponAccessoriesCargo` | 1.22 |
| `addBackpackGlobal` | 1.32 |
| `removeBackpackGlobal` | 1.32 |
| `addWeaponItem` | 1.38 |
| `removeSecondaryWeaponItem` | 1.38 |
| `currentThrowable` | 1.48 |
| `getUnitLoadout` | 1.58 |
| `setUnitLoadout` | 1.58 |
| `getContainerMaxLoad` | 1.62 |
| `lockInventory` | 2.0 |
| `lockedInventory` | 2.0 |
| `addBinocularItem` | 2.2 |
| `binocularItems` | 2.2 |
| `binocularMagazine` | 2.2 |
| `removeAllBinocularItems` | 2.2 |
| `removeAllSecondaryWeaponItems` | 2.2 |
| `removeBinocularItem` | 2.2 |
| `uniqueUnitItems` | 2.6 |
| `maxLoad` | 2.8 |
| `setMaxLoad` | 2.8 |
| `getCorpse` | 2.12 |
| `backpacks` | 2.14 |
| `getSlotItemName` | 2.14 |
| `getCorpseWeaponholders` | 2.18 |
| `isThrowable` | 2.18 |
| `selectThrowable` | 2.18 |
| `throwables` | 2.18 |
| `isSwitchingWeapon` | 2.20 |
| `removeAllMagazines` | 2.20 |
| `removeWeaponItem` | 2.22 |
| `removeClothing` | n/v |

#### Stamina System (21 commands, since 0.50 to 1.62)

| Command | Since |
|---|---|
| `enableFatigue` | 0.50 |
| `forceWalk` | 0.50 |
| `getFatigue` | 0.50 |
| `isForcedWalk` | 0.50 |
| `setFatigue` | 0.50 |
| `allowSprint` | 1.54 |
| `enableStamina` | 1.54 |
| `getAnimAimPrecision` | 1.54 |
| `getAnimSpeedCoef` | 1.54 |
| `getCustomAimCoef` | 1.54 |
| `getStamina` | 1.54 |
| `isAimPrecisionEnabled` | 1.54 |
| `isSprintAllowed` | 1.54 |
| `isStaminaEnabled` | 1.54 |
| `setAnimSpeedCoef` | 1.54 |
| `setCustomAimCoef` | 1.54 |
| `setStamina` | 1.54 |
| `setStaminaScheme` | 1.54 |
| `enableAimPrecision` | 1.62 |
| `getAimingCoef` | 1.62 |
| `getWeaponSway` | 1.62 |

#### Containers (48 commands, since 0.50 to 1.22)

| Command | Since |
|---|---|
| `addBackpack` | 0.50 |
| `addBackpackCargo` | 0.50 |
| `addBackpackCargoGlobal` | 0.50 |
| `addMagazineCargo` | 0.50 |
| `addMagazineCargoGlobal` | 0.50 |
| `addWeaponCargo` | 0.50 |
| `addWeaponCargoGlobal` | 0.50 |
| `backpack` | 0.50 |
| `backpackCargo` | 0.50 |
| `backpackItems` | 0.50 |
| `backpackMagazines` | 0.50 |
| `backpackSpaceFor` | 0.50 |
| `clearAllItemsFromBackpack` | 0.50 |
| `clearBackpackCargo` | 0.50 |
| `clearBackpackCargoGlobal` | 0.50 |
| `clearItemCargo` | 0.50 |
| `clearItemCargoGlobal` | 0.50 |
| `clearMagazineCargo` | 0.50 |
| `clearMagazineCargoGlobal` | 0.50 |
| `clearWeaponCargo` | 0.50 |
| `clearWeaponCargoGlobal` | 0.50 |
| `firstBackpack` | 0.50 |
| `getBackpackCargo` | 0.50 |
| `getMagazineCargo` | 0.50 |
| `getWeaponCargo` | 0.50 |
| `loadBackpack` | 0.50 |
| `magazineCargo` | 0.50 |
| `removeBackpack` | 0.50 |
| `removeUniform` | 0.50 |
| `removeVest` | 0.50 |
| `uniform` | 0.50 |
| `uniformMagazines` | 0.50 |
| `unitBackpack` | 0.50 |
| `vest` | 0.50 |
| `weaponCargo` | 0.50 |
| `addItemToBackpack` | 1.4 |
| `backpackContainer` | 1.4 |
| `canAddItemToBackpack` | 1.4 |
| `everyBackpack` | 1.4 |
| `removeAllItemsWithMagazines` | 1.4 |
| `removeItemFromBackpack` | 1.4 |
| `removeItemFromUniform` | 1.4 |
| `removeItemFromVest` | 1.4 |
| `uniformContainer` | 1.4 |
| `vestContainer` | 1.4 |
| `forceAddUniform` | 1.22 |
| `weaponAccessoriesCargo` | 1.22 |
| `weaponsItemsCargo` | 1.22 |

### Unit and group control

#### Unit Control (81 commands, since 0.50 to 2.18)

| Command | Since |
|---|---|
| `allowGetIn` | 0.50 |
| `assignAsCargo` | 0.50 |
| `assignAsCargoIndex` | 0.50 |
| `assignAsCommander` | 0.50 |
| `assignAsDriver` | 0.50 |
| `assignAsGunner` | 0.50 |
| `assignedCargo` | 0.50 |
| `assignedCommander` | 0.50 |
| `assignedDriver` | 0.50 |
| `assignedGunner` | 0.50 |
| `attackEnabled` | 0.50 |
| `commandFSM` | 0.50 |
| `commandFire` | 0.50 |
| `commandFollow` | 0.50 |
| `commandGetOut` | 0.50 |
| `commandWatch` | 0.50 |
| `currentCommand` | 0.50 |
| `doFSM` | 0.50 |
| `doFire` | 0.50 |
| `doFollow` | 0.50 |
| `doGetOut` | 0.50 |
| `doMove` | 0.50 |
| `doStop` | 0.50 |
| `doTarget` | 0.50 |
| `doWatch` | 0.50 |
| `effectiveCommander` | 0.50 |
| `emptyPositions` | 0.50 |
| `enableAttack` | 0.50 |
| `expectedDestination` | 0.50 |
| `fire` | 0.50 |
| `fireAtTarget` | 0.50 |
| `forceWeaponFire` | 0.50 |
| `formLeader` | 0.50 |
| `formationLeader` | 0.50 |
| `glanceAt` | 0.50 |
| `in` | 0.50 |
| `land` | 0.50 |
| `landAt` | 0.50 |
| `landResult` | 0.50 |
| `leaveVehicle` | 0.50 |
| `limitSpeed` | 0.50 |
| `lookAt` | 0.50 |
| `move` | 0.50 |
| `moveInCargo` | 0.50 |
| `moveInCommander` | 0.50 |
| `moveInDriver` | 0.50 |
| `moveInGunner` | 0.50 |
| `moveOut` | 0.50 |
| `moveTo` | 0.50 |
| `moveToCompleted` | 0.50 |
| `moveToFailed` | 0.50 |
| `orderGetIn` | 0.50 |
| `playAction` | 0.50 |
| `sendSimpleCommand` | 0.50 |
| `setDestination` | 0.50 |
| `setFormationTask` | 0.50 |
| `setUnitPos` | 0.50 |
| `setUnitPosWeak` | 0.50 |
| `stance` | 0.50 |
| `stop` | 0.50 |
| `stopped` | 0.50 |
| `suppressFor` | 0.50 |
| `swimInDepth` | 0.50 |
| `switchAction` | 0.50 |
| `unassignVehicle` | 0.50 |
| `unitPos` | 0.50 |
| `unitReady` | 0.50 |
| `weaponDirection` | 0.50 |
| `moveInAny` | 1.18 |
| `setUnloadInCombat` | 1.36 |
| `commandSuppressiveFire` | 1.60 |
| `doSuppressiveFire` | 1.60 |
| `forceFollowRoad` | 1.64 |
| `forgetTarget` | 1.70 |
| `setEffectiveCommander` | 1.96 |
| `vehicleMoveInfo` | 1.98 |
| `getCruiseControl` | 2.6 |
| `setCruiseControl` | 2.6 |
| `pose` | 2.8 |
| `getLeaning` | 2.18 |
| `hideBehindScripted` | n/v |

#### Groups (50 commands, since 0.50 to 2.14)

| Command | Since |
|---|---|
| `allGroups` | 0.50 |
| `allowFleeing` | 0.50 |
| `assignTeam` | 0.50 |
| `attackEnabled` | 0.50 |
| `combatMode` | 0.50 |
| `commandMove` | 0.50 |
| `commandStop` | 0.50 |
| `commandTarget` | 0.50 |
| `createGroup` | 0.50 |
| `deleteGroup` | 0.50 |
| `dissolveTeam` | 0.50 |
| `enableAttack` | 0.50 |
| `formation` | 0.50 |
| `formationDirection` | 0.50 |
| `formationMembers` | 0.50 |
| `formationTask` | 0.50 |
| `group` | 0.50 |
| `groupFromNetId` | 0.50 |
| `groupId` | 0.50 |
| `grpNull` | 0.50 |
| `isFormationLeader` | 0.50 |
| `join` | 0.50 |
| `joinAs` | 0.50 |
| `joinAsSilent` | 0.50 |
| `joinSilent` | 0.50 |
| `leader` | 0.50 |
| `leaveVehicle` | 0.50 |
| `onBriefingGroup` | 0.50 |
| `resetSubgroupDirection` | 0.50 |
| `selectLeader` | 0.50 |
| `setBehaviour` | 0.50 |
| `setCombatMode` | 0.50 |
| `setFormDir` | 0.50 |
| `setFormation` | 0.50 |
| `setGroupId` | 0.50 |
| `setSpeedMode` | 0.50 |
| `speedMode` | 0.50 |
| `unassignTeam` | 0.50 |
| `units` | 0.50 |
| `setGroupIdGlobal` | 1.48 |
| `deleteGroupWhenEmpty` | 1.68 |
| `isGroupDeletedWhenEmpty` | 1.68 |
| `forgetTarget` | 1.70 |
| `setBehaviourStrong` | 1.92 |
| `combatBehaviour` | 2.4 |
| `setCombatBehaviour` | 2.4 |
| `assignedGroup` | 2.12 |
| `assignedVehicles` | 2.12 |
| `groups` | 2.12 |
| `inAreaArrayIndexes` | 2.14 |

#### Waypoints (63 commands, since 0.50 to 2.00)

| Command | Since |
|---|---|
| `addWaypoint` | 0.50 |
| `copyWaypoints` | 0.50 |
| `createGuardedPoint` | 0.50 |
| `currentWaypoint` | 0.50 |
| `deleteWaypoint` | 0.50 |
| `getWPPos` | 0.50 |
| `lockWP` | 0.50 |
| `setCurrentWaypoint` | 0.50 |
| `setMusicEffect` | 0.50 |
| `setSoundEffect` | 0.50 |
| `setTitleEffect` | 0.50 |
| `setWPPos` | 0.50 |
| `setWaypointBehaviour` | 0.50 |
| `setWaypointCombatMode` | 0.50 |
| `setWaypointCompletionRadius` | 0.50 |
| `setWaypointDescription` | 0.50 |
| `setWaypointFormation` | 0.50 |
| `setWaypointHousePosition` | 0.50 |
| `setWaypointName` | 0.50 |
| `setWaypointPosition` | 0.50 |
| `setWaypointScript` | 0.50 |
| `setWaypointSpeed` | 0.50 |
| `setWaypointStatements` | 0.50 |
| `setWaypointTimeout` | 0.50 |
| `setWaypointType` | 0.50 |
| `setWaypointVisible` | 0.50 |
| `showWaypoint` | 0.50 |
| `synchronizeTrigger` | 0.50 |
| `synchronizeWaypoint` | 0.50 |
| `synchronizedWaypoints` | 0.50 |
| `waypointAttachObject` | 0.50 |
| `waypointAttachVehicle` | 0.50 |
| `waypointAttachedObject` | 0.50 |
| `waypointAttachedVehicle` | 0.50 |
| `waypointBehaviour` | 0.50 |
| `waypointCombatMode` | 0.50 |
| `waypointCompletionRadius` | 0.50 |
| `waypointDescription` | 0.50 |
| `waypointFormation` | 0.50 |
| `waypointHousePosition` | 0.50 |
| `waypointName` | 0.50 |
| `waypointPosition` | 0.50 |
| `waypointScript` | 0.50 |
| `waypointShow` | 0.50 |
| `waypointSpeed` | 0.50 |
| `waypointStatements` | 0.50 |
| `waypointTimeout` | 0.50 |
| `waypointType` | 0.50 |
| `waypointVisible` | 0.50 |
| `waypoints` | 0.50 |
| `setWaypointLoiterRadius` | 1.0 |
| `setWaypointLoiterType` | 1.0 |
| `showWaypoints` | 1.0 |
| `waypointLoiterRadius` | 1.0 |
| `waypointLoiterType` | 1.0 |
| `waypointTimeoutCurrent` | 1.8 |
| `enableUAVWaypoints` | 1.40 |
| `waypointsEnabledUAV` | 1.40 |
| `setWaypointForceBehaviour` | 1.58 |
| `waypointForceBehaviour` | 1.58 |
| `customWaypointPosition` | 1.92 |
| `setWaypointLoiterAltitude` | 2.0 |
| `waypointLoiterAltitude` | 2.0 |

#### High Command (27 commands, since 0.50)

| Command | Since |
|---|---|
| `addGroupIcon` | 0.50 |
| `clearGroupIcons` | 0.50 |
| `getGroupIcon` | 0.50 |
| `getGroupIconParams` | 0.50 |
| `getGroupIcons` | 0.50 |
| `groupIconSelectable` | 0.50 |
| `groupIconsVisible` | 0.50 |
| `hcAllGroups` | 0.50 |
| `hcGroupParams` | 0.50 |
| `hcLeader` | 0.50 |
| `hcRemoveAllGroups` | 0.50 |
| `hcRemoveGroup` | 0.50 |
| `hcSelectGroup` | 0.50 |
| `hcSelected` | 0.50 |
| `hcSetGroup` | 0.50 |
| `hcShowBar` | 0.50 |
| `hcShownBar` | 0.50 |
| `onCommandModeChanged` | 0.50 |
| `onGroupIconClick` | 0.50 |
| `onGroupIconOverEnter` | 0.50 |
| `onGroupIconOverLeave` | 0.50 |
| `onHCGroupSelectionChanged` | 0.50 |
| `removeGroupIcon` | 0.50 |
| `setGroupIcon` | 0.50 |
| `setGroupIconParams` | 0.50 |
| `setGroupIconsSelectable` | 0.50 |
| `setGroupIconsVisible` | 0.50 |

#### Remote Control (21 commands, since 0.50 to 2.16)

| Command | Since |
|---|---|
| `cameraOn` | 0.50 |
| `remoteControl` | 0.50 |
| `allUnitsUAV` | 0.76 |
| `connectTerminalToUAV` | 0.76 |
| `getConnectedUAV` | 0.76 |
| `isUAVConnected` | 0.76 |
| `UAVControl` | 1.0 |
| `isAutonomous` | 1.16 |
| `setAutonomous` | 1.16 |
| `showUAVFeed` | 1.16 |
| `shownUAVFeed` | 1.16 |
| `disableUAVConnectability` | 1.24 |
| `enableUAVConnectability` | 1.24 |
| `isUAVConnectable` | 1.24 |
| `enableUAVWaypoints` | 1.40 |
| `waypointsEnabledUAV` | 1.40 |
| `unitIsUAV` | 1.64 |
| `getConnectedUAVUnit` | 2.8 |
| `isRemoteControlling` | 2.14 |
| `remoteControlled` | 2.14 |
| `focusOn` | 2.16 |

#### Team Switch (8 commands, since 0.50)

| Command | Since |
|---|---|
| `addSwitchableUnit` | 0.50 |
| `enableTeamSwitch` | 0.50 |
| `onBriefingTeamSwitch` | 0.50 |
| `onTeamSwitch` | 0.50 |
| `removeSwitchableUnit` | 0.50 |
| `switchableUnits` | 0.50 |
| `teamSwitch` | 0.50 |
| `teamSwitchEnabled` | 0.50 |

#### Teams (22 commands, since 0.50)

| Command | Since |
|---|---|
| `addResources` | 0.50 |
| `addTeamMember` | 0.50 |
| `agent` | 0.50 |
| `agents` | 0.50 |
| `createTask` | 0.50 |
| `createTeam` | 0.50 |
| `currentTasks` | 0.50 |
| `deleteResources` | 0.50 |
| `deleteTeam` | 0.50 |
| `isAgent` | 0.50 |
| `members` | 0.50 |
| `registerTask` | 0.50 |
| `registeredTasks` | 0.50 |
| `removeTeamMember` | 0.50 |
| `resources` | 0.50 |
| `sendTask` | 0.50 |
| `setLeader` | 0.50 |
| `teamMember` | 0.50 |
| `teamMemberNull` | 0.50 |
| `teamName` | 0.50 |
| `teamType` | 0.50 |
| `teams` | 0.50 |

#### Sides (38 commands, since 0.50 to 1.58)

| Command | Since |
|---|---|
| `WFSideText` | 0.50 |
| `airportSide` | 0.50 |
| `allSites` | 0.50 |
| `blufor` | 0.50 |
| `captive` | 0.50 |
| `captiveNum` | 0.50 |
| `civilian` | 0.50 |
| `countEnemy` | 0.50 |
| `countFriendly` | 0.50 |
| `countSide` | 0.50 |
| `countUnknown` | 0.50 |
| `createCenter` | 0.50 |
| `createSite` | 0.50 |
| `deleteCenter` | 0.50 |
| `east` | 0.50 |
| `faction` | 0.50 |
| `getFriend` | 0.50 |
| `independent` | 0.50 |
| `knowsAbout` | 0.50 |
| `opfor` | 0.50 |
| `playerSide` | 0.50 |
| `resistance` | 0.50 |
| `scoreSide` | 0.50 |
| `setAirportSide` | 0.50 |
| `setCaptive` | 0.50 |
| `setFriend` | 0.50 |
| `setSide` | 0.50 |
| `side` | 0.50 |
| `sideEnemy` | 0.50 |
| `sideFriendly` | 0.50 |
| `sideLogic` | 0.50 |
| `sideUnknown` | 0.50 |
| `west` | 0.50 |
| `addScoreSide` | 1.12 |
| `sideAmbientLife` | 1.58 |
| `sideEmpty` | 1.58 |
| `enemy` | n/v |
| `friendly` | n/v |

#### Flags (11 commands, since 0.50 to 1.70)

| Command | Since |
|---|---|
| `flag` | 0.50 |
| `flagOwner` | 0.50 |
| `setFlagOwner` | 0.50 |
| `setFlagSide` | 0.50 |
| `setFlagTexture` | 0.50 |
| `flagSide` | 1.54 |
| `flagTexture` | 1.54 |
| `flagAnimationPhase` | 1.68 |
| `setFlagAnimationPhase` | 1.68 |
| `forceFlagTexture` | 1.70 |
| `getForcedFlagTexture` | 1.70 |

#### Sensors (19 commands, since 1.52 to 2.22)

| Command | Since |
|---|---|
| `getRemoteSensorsDisabled` | 1.52 |
| `confirmSensorTarget` | 1.70 |
| `reportRemoteTarget` | 1.70 |
| `setVehicleRadar` | 1.70 |
| `setVehicleReceiveRemoteTargets` | 1.70 |
| `setVehicleReportOwnPosition` | 1.70 |
| `setVehicleReportRemoteTargets` | 1.70 |
| `vehicleReceiveRemoteTargets` | 1.70 |
| `vehicleReportOwnPosition` | 1.70 |
| `vehicleReportRemoteTargets` | 1.70 |
| `enableVehicleSensor` | 1.72 |
| `isSensorTargetConfirmed` | 1.72 |
| `isVehicleRadarOn` | 1.72 |
| `isVehicleSensorEnabled` | 1.72 |
| `listRemoteTargets` | 1.72 |
| `listVehicleSensors` | 1.72 |
| `getSensorTargets` | 2.6 |
| `getSensorThreats` | 2.6 |
| `setTargetSize` | 2.22 |

#### Object Detection (42 commands, since 0.50 to 2.18)

| Command | Since |
|---|---|
| `agents` | 0.50 |
| `allDead` | 0.50 |
| `allDeadMen` | 0.50 |
| `allGroups` | 0.50 |
| `allMissionObjects` | 0.50 |
| `allUnits` | 0.50 |
| `countEnemy` | 0.50 |
| `countSide` | 0.50 |
| `countType` | 0.50 |
| `cursorTarget` | 0.50 |
| `entities` | 0.50 |
| `findNearestEnemy` | 0.50 |
| `nearEntities` | 0.50 |
| `nearObjects` | 0.50 |
| `nearObjectsReady` | 0.50 |
| `nearRoads` | 0.50 |
| `nearSupplies` | 0.50 |
| `nearTargets` | 0.50 |
| `nearestBuilding` | 0.50 |
| `nearestObject` | 0.50 |
| `nearestObjects` | 0.50 |
| `playableUnits` | 0.50 |
| `switchableUnits` | 0.50 |
| `targetsQuery` | 0.50 |
| `units` | 0.50 |
| `unitsBelowHeight` | 0.50 |
| `vehicles` | 0.50 |
| `allUnitsUAV` | 0.76 |
| `allCurators` | 1.16 |
| `allPlayers` | 1.48 |
| `targetKnowledge` | 1.50 |
| `nearestTerrainObjects` | 1.54 |
| `cursorObject` | 1.56 |
| `allSimpleObjects` | 1.68 |
| `getCursorObjectParams` | 1.70 |
| `targets` | 1.70 |
| `allUsers` | 2.6 |
| `getUserInfo` | 2.6 |
| `allObjects` | 2.10 |
| `nearestMines` | 2.10 |
| `ignoreTarget` | 2.18 |
| `object` | n/v |

#### Interaction (67 commands, since 0.50 to 2.22)

| Command | Since |
|---|---|
| `HUDMovementLevels` | 0.50 |
| `action` | 0.50 |
| `actionKeys` | 0.50 |
| `actionKeysImages` | 0.50 |
| `actionKeysNames` | 0.50 |
| `actionKeysNamesArray` | 0.50 |
| `actionName` | 0.50 |
| `addAction` | 0.50 |
| `commandingMenu` | 0.50 |
| `disableUserInput` | 0.50 |
| `drawIcon3D` | 0.50 |
| `drawLine3D` | 0.50 |
| `forceMap` | 0.50 |
| `groupSelectUnit` | 0.50 |
| `groupSelectedUnits` | 0.50 |
| `hint` | 0.50 |
| `hintC` | 0.50 |
| `hintCadet` | 0.50 |
| `hintSilent` | 0.50 |
| `inGameUISetEventHandler` | 0.50 |
| `inputAction` | 0.50 |
| `openMap` | 0.50 |
| `removeAction` | 0.50 |
| `removeAllActions` | 0.50 |
| `setCompassOscillation` | 0.50 |
| `setHUDMovementLevels` | 0.50 |
| `setRadioMsg` | 0.50 |
| `setUserActionText` | 0.50 |
| `showCommandingMenu` | 0.50 |
| `showCompass` | 0.50 |
| `showGPS` | 0.50 |
| `showHUD` | 0.50 |
| `showPad` | 0.50 |
| `showRadio` | 0.50 |
| `showWarrant` | 0.50 |
| `showWatch` | 0.50 |
| `shownCompass` | 0.50 |
| `shownGPS` | 0.50 |
| `shownPad` | 0.50 |
| `shownRadio` | 0.50 |
| `shownWarrant` | 0.50 |
| `shownWatch` | 0.50 |
| `visibleMap` | 0.50 |
| `visibleCompass` | 1.22 |
| `visibleGPS` | 1.22 |
| `visibleWatch` | 1.22 |
| `shownHUD` | 1.52 |
| `showScoretable` | 1.60 |
| `shownScoretable` | 1.60 |
| `userInputDisabled` | 1.60 |
| `forcedMap` | 1.62 |
| `actionIDs` | 1.64 |
| `actionParams` | 1.64 |
| `visibleScoretable` | 1.64 |
| `getUserMFDValue` | 1.70 |
| `setUserMFDValue` | 1.70 |
| `isActionMenuVisible` | 1.96 |
| `openGPS` | 2.4 |
| `drawLaser` | 2.8 |
| `inputController` | 2.8 |
| `inputMouse` | 2.8 |
| `actionKeysEx` | 2.10 |
| `actionNow` | 2.18 |
| `setCompassDeclination` | 2.18 |
| `hiddenActions` | 2.22 |
| `hideActions` | 2.22 |
| `shownAction` | 2.22 |

#### Positions (52 commands, since 0.50 to 2.18)

| Command | Since |
|---|---|
| `ASLToATL` | 0.50 |
| `ATLToASL` | 0.50 |
| `aimPos` | 0.50 |
| `buildingPos` | 0.50 |
| `eyePos` | 0.50 |
| `findEmptyPosition` | 0.50 |
| `findEmptyPositionReady` | 0.50 |
| `formationPosition` | 0.50 |
| `getPos` | 0.50 |
| `getPosASL` | 0.50 |
| `getPosASLW` | 0.50 |
| `getPosATL` | 0.50 |
| `getTerrainHeightASL` | 0.50 |
| `isFlatEmpty` | 0.50 |
| `mapGridPosition` | 0.50 |
| `modelToWorld` | 0.50 |
| `posScreenToWorld` | 0.50 |
| `posWorldToScreen` | 0.50 |
| `position` | 0.50 |
| `positionCameraToWorld` | 0.50 |
| `screenToWorld` | 0.50 |
| `setPos` | 0.50 |
| `setPosASL` | 0.50 |
| `setPosASL2` | 0.50 |
| `setPosASLW` | 0.50 |
| `setPosATL` | 0.50 |
| `setVehiclePosition` | 0.50 |
| `surfaceIsWater` | 0.50 |
| `surfaceNormal` | 0.50 |
| `surfaceType` | 0.50 |
| `unitsBelowHeight` | 0.50 |
| `visiblePosition` | 0.50 |
| `visiblePositionASL` | 0.50 |
| `worldToModel` | 0.50 |
| `worldToScreen` | 0.50 |
| `getPosWorld` | 1.32 |
| `setPosWorld` | 1.32 |
| `worldToModelVisual` | 1.32 |
| `AGLToASL` | 1.50 |
| `ASLToAGL` | 1.50 |
| `inPolygon` | 1.54 |
| `getRelPos` | 1.56 |
| `inArea` | 1.58 |
| `unitAimPosition` | 1.64 |
| `inAreaArray` | 1.66 |
| `modelToWorldWorld` | 1.70 |
| `surfaceTexture` | 2.0 |
| `getTerrainHeight` | 2.10 |
| `getTerrainInfo` | 2.10 |
| `setTerrainHeight` | 2.10 |
| `inAreaArrayIndexes` | 2.14 |
| `screenToWorldDirection` | 2.18 |

#### Unit Identity (20 commands, since 0.50 to 2.18)

| Command | Since |
|---|---|
| `deleteIdentity` | 0.50 |
| `loadIdentity` | 0.50 |
| `name` | 0.50 |
| `rank` | 0.50 |
| `rankId` | 0.50 |
| `saveIdentity` | 0.50 |
| `setFace` | 0.50 |
| `setIdentity` | 0.50 |
| `setMimic` | 0.50 |
| `setName` | 0.50 |
| `setRank` | 0.50 |
| `setUnitRank` | 0.50 |
| `face` | 1.2 |
| `pitch` | 1.2 |
| `setNameSound` | 1.2 |
| `setPitch` | 1.2 |
| `setSpeaker` | 1.2 |
| `speaker` | 1.2 |
| `lockIdentity` | 1.56 |
| `hasCustomFace` | 2.18 |

#### Triggers (33 commands, since 0.50 to 2.14)

| Command | Since |
|---|---|
| `createTrigger` | 0.50 |
| `list` | 0.50 |
| `setEffectCondition` | 0.50 |
| `setMusicEffect` | 0.50 |
| `setRadioMsg` | 0.50 |
| `setSoundEffect` | 0.50 |
| `setTitleEffect` | 0.50 |
| `setTriggerActivation` | 0.50 |
| `setTriggerArea` | 0.50 |
| `setTriggerStatements` | 0.50 |
| `setTriggerText` | 0.50 |
| `setTriggerTimeout` | 0.50 |
| `setTriggerType` | 0.50 |
| `synchronizeTrigger` | 0.50 |
| `synchronizeWaypoint` | 0.50 |
| `synchronizedTriggers` | 0.50 |
| `synchronizedWaypoints` | 0.50 |
| `triggerActivated` | 0.50 |
| `triggerActivation` | 0.50 |
| `triggerArea` | 0.50 |
| `triggerAttachObject` | 0.50 |
| `triggerAttachVehicle` | 0.50 |
| `triggerAttachedVehicle` | 0.50 |
| `triggerStatements` | 0.50 |
| `triggerText` | 0.50 |
| `triggerTimeout` | 0.50 |
| `triggerType` | 0.50 |
| `triggerTimeoutCurrent` | 1.8 |
| `inArea` | 1.58 |
| `inAreaArray` | 1.66 |
| `setTriggerInterval` | 1.98 |
| `triggerInterval` | 1.98 |
| `inAreaArrayIndexes` | 2.14 |

### Mission and data

#### Mission Information (41 commands, since 0.50 to 2.20)

| Command | Since |
|---|---|
| `activateKey` | 0.50 |
| `dayTime` | 0.50 |
| `deActivateKey` | 0.50 |
| `enableEndDialog` | 0.50 |
| `enableSaving` | 0.50 |
| `endMission` | 0.50 |
| `estimatedEndServerTime` | 0.50 |
| `estimatedTimeLeft` | 0.50 |
| `failMission` | 0.50 |
| `forceEnd` | 0.50 |
| `isKeyActive` | 0.50 |
| `loadGame` | 0.50 |
| `loadStatus` | 0.50 |
| `missionName` | 0.50 |
| `missionStart` | 0.50 |
| `saveGame` | 0.50 |
| `saveStatus` | 0.50 |
| `savingEnabled` | 0.50 |
| `selectBestPlaces` | 0.50 |
| `serverTime` | 0.50 |
| `setDate` | 0.50 |
| `time` | 0.50 |
| `worldName` | 0.50 |
| `isSteamMission` | 0.74 |
| `markAsFinishedOnSteam` | 0.74 |
| `setTimeMultiplier` | 1.26 |
| `timeMultiplier` | 1.26 |
| `worldSize` | 1.48 |
| `getMissionConfig` | 1.56 |
| `getMissionConfigValue` | 1.56 |
| `getMissionLayerEntities` | 1.56 |
| `getMissionLayers` | 1.56 |
| `missionVersion` | 1.56 |
| `getMissionDLCs` | 1.62 |
| `missionDifficulty` | 1.62 |
| `getMissionPath` | 1.96 |
| `missionNameSource` | 2.2 |
| `missionEnd` | 2.6 |
| `isSaving` | 2.8 |
| `uiTime` | 2.20 |
| `getWorld` | n/v |

#### Config (28 commands, since 0.50 to 2.10)

| Command | Since |
|---|---|
| `/` | 0.50 |
| `>>` | 0.50 |
| `campaignConfigFile` | 0.50 |
| `configFile` | 0.50 |
| `configName` | 0.50 |
| `count` | 0.50 |
| `getArray` | 0.50 |
| `getNumber` | 0.50 |
| `getText` | 0.50 |
| `inheritsFrom` | 0.50 |
| `isArray` | 0.50 |
| `isClass` | 0.50 |
| `isNumber` | 0.50 |
| `isText` | 0.50 |
| `missionConfigFile` | 0.50 |
| `select` | 0.50 |
| `diag_mergeConfigFile` | 1.0 |
| `configClasses` | 1.24 |
| `configProperties` | 1.36 |
| `configHierarchy` | 1.48 |
| `configNull` | 1.56 |
| `getMissionConfig` | 1.56 |
| `getMissionConfigValue` | 1.56 |
| `configSourceAddonList` | 1.58 |
| `configOf` | 2.0 |
| `diag_exportConfig` | 2.2 |
| `getTextRaw` | 2.2 |
| `loadConfig` | 2.10 |

#### Locations (31 commands, since 0.50 to 2.14)

| Command | Since |
|---|---|
| `attachObject` | 0.50 |
| `className` | 0.50 |
| `createLocation` | 0.50 |
| `deleteLocation` | 0.50 |
| `direction` | 0.50 |
| `drawLocation` | 0.50 |
| `importance` | 0.50 |
| `in` | 0.50 |
| `locationNull` | 0.50 |
| `locationPosition` | 0.50 |
| `name` | 0.50 |
| `nearestLocation` | 0.50 |
| `nearestLocationWithDubbing` | 0.50 |
| `nearestLocations` | 0.50 |
| `rectangular` | 0.50 |
| `setDirection` | 0.50 |
| `setImportance` | 0.50 |
| `setName` | 0.50 |
| `setPosition` | 0.50 |
| `setRectangular` | 0.50 |
| `setSide` | 0.50 |
| `setSize` | 0.50 |
| `setText` | 0.50 |
| `setType` | 0.50 |
| `size` | 0.50 |
| `text` | 0.50 |
| `type` | 0.50 |
| `setSpeech` | 1.12 |
| `inArea` | 1.58 |
| `inAreaArray` | 1.66 |
| `inAreaArrayIndexes` | 2.14 |

#### Markers (49 commands, since 0.50 to 2.14)

| Command | Since |
|---|---|
| `allMapMarkers` | 0.50 |
| `createMarker` | 0.50 |
| `createMarkerLocal` | 0.50 |
| `deleteMarker` | 0.50 |
| `deleteMarkerLocal` | 0.50 |
| `getMarkerColor` | 0.50 |
| `getMarkerPos` | 0.50 |
| `getMarkerSize` | 0.50 |
| `getMarkerType` | 0.50 |
| `markerAlpha` | 0.50 |
| `markerBrush` | 0.50 |
| `markerColor` | 0.50 |
| `markerDir` | 0.50 |
| `markerPos` | 0.50 |
| `markerShape` | 0.50 |
| `markerSize` | 0.50 |
| `markerText` | 0.50 |
| `markerType` | 0.50 |
| `setMarkerAlpha` | 0.50 |
| `setMarkerAlphaLocal` | 0.50 |
| `setMarkerBrush` | 0.50 |
| `setMarkerBrushLocal` | 0.50 |
| `setMarkerColor` | 0.50 |
| `setMarkerColorLocal` | 0.50 |
| `setMarkerDir` | 0.50 |
| `setMarkerDirLocal` | 0.50 |
| `setMarkerPos` | 0.50 |
| `setMarkerPosLocal` | 0.50 |
| `setMarkerShape` | 0.50 |
| `setMarkerShapeLocal` | 0.50 |
| `setMarkerSize` | 0.50 |
| `setMarkerSizeLocal` | 0.50 |
| `setMarkerText` | 0.50 |
| `setMarkerTextLocal` | 0.50 |
| `setMarkerType` | 0.50 |
| `setMarkerTypeLocal` | 0.50 |
| `inArea` | 1.58 |
| `inAreaArray` | 1.66 |
| `getPlayerID` | 2.2 |
| `markerChannel` | 2.2 |
| `markerPolyline` | 2.2 |
| `setMarkerPolyline` | 2.2 |
| `setMarkerPolylineLocal` | 2.2 |
| `markerShadow` | 2.4 |
| `setMarkerShadow` | 2.4 |
| `setMarkerShadowLocal` | 2.4 |
| `inAreaArrayIndexes` | 2.14 |
| `markerDrawPriority` | 2.14 |
| `setMarkerDrawPriority` | 2.14 |

#### Map (14 commands, since 0.50 to 2.10)

| Command | Since |
|---|---|
| `forceMap` | 0.50 |
| `getElevationOffset` | 0.50 |
| `mapAnimAdd` | 0.50 |
| `mapAnimClear` | 0.50 |
| `mapAnimCommit` | 0.50 |
| `mapAnimDone` | 0.50 |
| `mapGridPosition` | 0.50 |
| `onMapSingleClick` | 0.50 |
| `openMap` | 0.50 |
| `showMap` | 0.50 |
| `shownMap` | 0.50 |
| `visibleMap` | 0.50 |
| `forcedMap` | 1.62 |
| `getObjectID` | 2.10 |

#### Briefing (63 commands, since 0.50 to 2.10)

| Command | Since |
|---|---|
| `cancelSimpleTaskDestination` | 0.50 |
| `createDiaryLink` | 0.50 |
| `createDiaryRecord` | 0.50 |
| `createDiarySubject` | 0.50 |
| `createSimpleTask` | 0.50 |
| `createTask` | 0.50 |
| `currentTask` | 0.50 |
| `currentTasks` | 0.50 |
| `debriefingText` | 0.50 |
| `diarySubjectExists` | 0.50 |
| `objStatus` | 0.50 |
| `onBriefingGroup` | 0.50 |
| `onBriefingNotes` | 0.50 |
| `onBriefingPlan` | 0.50 |
| `onBriefingTeamSwitch` | 0.50 |
| `priority` | 0.50 |
| `processDiaryLink` | 0.50 |
| `registerTask` | 0.50 |
| `registeredTasks` | 0.50 |
| `removeSimpleTask` | 0.50 |
| `selectDiarySubject` | 0.50 |
| `sendTask` | 0.50 |
| `sendTaskResult` | 0.50 |
| `setCurrentTask` | 0.50 |
| `setDebriefingText` | 0.50 |
| `setSimpleTaskDescription` | 0.50 |
| `setSimpleTaskDestination` | 0.50 |
| `setSimpleTaskTarget` | 0.50 |
| `setTaskResult` | 0.50 |
| `setTaskState` | 0.50 |
| `simpleTasks` | 0.50 |
| `taskChildren` | 0.50 |
| `taskCompleted` | 0.50 |
| `taskDescription` | 0.50 |
| `taskDestination` | 0.50 |
| `taskHint` | 0.50 |
| `taskNull` | 0.50 |
| `taskParent` | 0.50 |
| `taskResult` | 0.50 |
| `taskState` | 0.50 |
| `type` | 0.50 |
| `unregisterTask` | 0.50 |
| `disableDebriefingStats` | 1.0 |
| `enableDebriefingStats` | 1.0 |
| `briefingName` | 1.12 |
| `setSimpleTaskAlwaysVisible` | 1.58 |
| `setSimpleTaskCustomData` | 1.58 |
| `setSimpleTaskType` | 1.58 |
| `setTaskMarkerOffset` | 1.58 |
| `taskAlwaysVisible` | 1.58 |
| `taskCustomData` | 1.58 |
| `taskMarkerOffset` | 1.58 |
| `taskType` | 1.58 |
| `removeDiaryRecord` | 1.96 |
| `removeDiarySubject` | 1.96 |
| `setDiaryRecordText` | 1.96 |
| `diaryRecordNull` | 2.0 |
| `allDiarySubjects` | 2.4 |
| `setDiarySubjectPicture` | 2.4 |
| `taskName` | 2.4 |
| `getDebriefingText` | 2.6 |
| `allDiaryRecords` | 2.10 |
| `onBriefingGear` | n/v |

#### Namespaces (16 commands, since 0.50 to 2.10)

| Command | Since |
|---|---|
| `disableSerialization` | 0.50 |
| `getVariable` | 0.50 |
| `missionNamespace` | 0.50 |
| `parsingNamespace` | 0.50 |
| `profileNamespace` | 0.50 |
| `saveProfileNamespace` | 0.50 |
| `setVariable` | 0.50 |
| `uiNamespace` | 0.50 |
| `with` | 0.50 |
| `allVariables` | 1.38 |
| `currentNamespace` | 1.48 |
| `localNamespace` | 2.0 |
| `serverNamespace` | 2.6 |
| `isMissionProfileNamespaceLoaded` | 2.10 |
| `missionProfileNamespace` | 2.10 |
| `saveMissionProfileNamespace` | 2.10 |

#### Variables (62 commands, since 0.50 to 2.18)

| Command | Since |
|---|---|
| `!` | 0.50 |
| `!=` | 0.50 |
| `&&` | 0.50 |
| `<` | 0.50 |
| `<=` | 0.50 |
| `=` | 0.50 |
| `==` | 0.50 |
| `>` | 0.50 |
| `>=` | 0.50 |
| `addPublicVariableEventHandler` | 0.50 |
| `and` | 0.50 |
| `displayNull` | 0.50 |
| `false` | 0.50 |
| `getFSMVariable` | 0.50 |
| `getVariable` | 0.50 |
| `isNil` | 0.50 |
| `isNull` | 0.50 |
| `locationNull` | 0.50 |
| `missionNamespace` | 0.50 |
| `nil` | 0.50 |
| `not` | 0.50 |
| `objNull` | 0.50 |
| `or` | 0.50 |
| `parsingNamespace` | 0.50 |
| `private` | 0.50 |
| `profileNamespace` | 0.50 |
| `publicVariable` | 0.50 |
| `publicVariableClient` | 0.50 |
| `publicVariableServer` | 0.50 |
| `saveProfileNamespace` | 0.50 |
| `saveVar` | 0.50 |
| `setVariable` | 0.50 |
| `taskNull` | 0.50 |
| `true` | 0.50 |
| `typeName` | 0.50 |
| `uiNamespace` | 0.50 |
| `||` | 0.50 |
| `netObjNull` | 1.0 |
| `isEqualTo` | 1.16 |
| `scriptNull` | 1.32 |
| `allVariables` | 1.38 |
| `param` | 1.48 |
| `params` | 1.48 |
| `isEqualType` | 1.54 |
| `isEqualTypeAll` | 1.54 |
| `isEqualTypeAny` | 1.54 |
| `isEqualTypeArray` | 1.54 |
| `isEqualTypeParams` | 1.54 |
| `configNull` | 1.56 |
| `#` | 1.82 |
| `diaryRecordNull` | 2.0 |
| `isFinal` | 2.0 |
| `localNamespace` | 2.0 |
| `isNotEqualTo` | 2.2 |
| `serverNamespace` | 2.6 |
| `isMissionProfileNamespaceLoaded` | 2.10 |
| `missionProfileNamespace` | 2.10 |
| `saveMissionProfileNamespace` | 2.10 |
| `isEqualRef` | 2.12 |
| `isNotEqualRef` | 2.12 |
| `import` | 2.18 |
| `privateAll` | 2.18 |

#### Multiplayer (79 commands, since 0.50 to 2.20)

| Command | Since |
|---|---|
| `addMPEventHandler` | 0.50 |
| `addPublicVariableEventHandler` | 0.50 |
| `addScore` | 0.50 |
| `estimatedEndServerTime` | 0.50 |
| `estimatedTimeLeft` | 0.50 |
| `getPlayerUID` | 0.50 |
| `getVariable` | 0.50 |
| `groupFromNetId` | 0.50 |
| `hasInterface` | 0.50 |
| `hostMission` | 0.50 |
| `isDedicated` | 0.50 |
| `isMultiplayer` | 0.50 |
| `isPlayer` | 0.50 |
| `isServer` | 0.50 |
| `local` | 0.50 |
| `netId` | 0.50 |
| `objectFromNetId` | 0.50 |
| `onPlayerConnected` | 0.50 |
| `onPlayerDisconnected` | 0.50 |
| `owner` | 0.50 |
| `playableUnits` | 0.50 |
| `playerRespawnTime` | 0.50 |
| `playersNumber` | 0.50 |
| `publicVariable` | 0.50 |
| `publicVariableClient` | 0.50 |
| `publicVariableServer` | 0.50 |
| `removeAllMPEventHandlers` | 0.50 |
| `removeMPEventHandler` | 0.50 |
| `removeSwitchableUnit` | 0.50 |
| `respawnVehicle` | 0.50 |
| `score` | 0.50 |
| `scoreSide` | 0.50 |
| `selectPlayer` | 0.50 |
| `sendAUMessage` | 0.50 |
| `sendUDPMessage` | 0.50 |
| `serverCommand` | 0.50 |
| `serverCommandAvailable` | 0.50 |
| `serverTime` | 0.50 |
| `setOwner` | 0.50 |
| `setPlayable` | 0.50 |
| `setPlayerRespawnTime` | 0.50 |
| `setVariable` | 0.50 |
| `switchableUnits` | 0.50 |
| `forceRespawn` | 1.4 |
| `playableSlotsNumber` | 1.6 |
| `getClientState` | 1.8 |
| `addScoreSide` | 1.12 |
| `serverCommandExecutable` | 1.34 |
| `groupOwner` | 1.40 |
| `setGroupOwner` | 1.40 |
| `allPlayers` | 1.48 |
| `roleDescription` | 1.48 |
| `serverName` | 1.48 |
| `didJIP` | 1.50 |
| `didJIPOwner` | 1.50 |
| `remoteExec` | 1.50 |
| `remoteExecCall` | 1.50 |
| `disableRemoteSensors` | 1.52 |
| `clientOwner` | 1.56 |
| `exportJIPMessages` | 1.56 |
| `getClientStateNumber` | 1.56 |
| `getPlayerScores` | 1.56 |
| `logNetwork` | 1.56 |
| `logNetworkTerminate` | 1.56 |
| `addPlayerScores` | 1.62 |
| `isMultiplayerSolo` | 1.66 |
| `isRemoteExecuted` | 1.66 |
| `isRemoteExecutedJIP` | 1.68 |
| `admin` | 1.70 |
| `remoteExecutedOwner` | 1.70 |
| `localNamespace` | 2.0 |
| `getPlayerID` | 2.2 |
| `allUsers` | 2.6 |
| `getUserInfo` | 2.6 |
| `serverNamespace` | 2.6 |
| `getRespawnVehicleInfo` | 2.18 |
| `remoteExecutedJIPID` | 2.18 |
| `getServerInfo` | 2.20 |
| `getPlayerUIDOld` | n/v |

#### Mods and Addons (11 commands, since 0.50 to 2.00)

| Command | Since |
|---|---|
| `activateAddons` | 0.50 |
| `verifySignature` | 0.50 |
| `unitAddons` | 1.0 |
| `activatedAddons` | 1.14 |
| `configSourceMod` | 1.38 |
| `configSourceModList` | 1.40 |
| `configSourceAddonList` | 1.58 |
| `modParams` | 1.62 |
| `addonFiles` | 2.0 |
| `allAddonsInfo` | 2.0 |
| `getLoadedModsInfo` | 2.0 |

#### Difficulty (11 commands, since 0.50 to 2.02)

| Command | Since |
|---|---|
| `cadetMode` | 0.50 |
| `difficultyEnabled` | 0.50 |
| `hintCadet` | 0.50 |
| `isTutHintsEnabled` | 0.50 |
| `difficulty` | 0.56 |
| `isInstructorFigureEnabled` | 1.4 |
| `difficultyEnabledRTD` | 1.34 |
| `difficultyOption` | 1.58 |
| `missionDifficulty` | 1.62 |
| `disableMapIndicators` | 1.82 |
| `forceCadetDifficulty` | 2.2 |

#### DLC (11 commands, since 1.00 to 2.00)

| Command | Since |
|---|---|
| `getDLCUsageTime` | 1.0 |
| `isDLCAvailable` | 1.0 |
| `getDLCAssetsUsage` | 1.16 |
| `getDLCAssetsUsageByName` | 1.16 |
| `getDLCs` | 1.16 |
| `getTotalDLCUsageTime` | 1.16 |
| `getObjectDLC` | 1.36 |
| `getPersonUsedDLCs` | 1.36 |
| `getMissionDLCs` | 1.62 |
| `openDLCPage` | 1.62 |
| `getAssetDLCInfo` | 2.0 |

#### Leaderboards (9 commands, since 1.42 to 1.56)

| Command | Since |
|---|---|
| `leaderboardRequestRowsFriends` | 1.42 |
| `leaderboardState` | 1.42 |
| `leaderboardsRequestUploadScore` | 1.42 |
| `leaderboardsRequestUploadScoreKeepBest` | 1.42 |
| `leaderboardDeInit` | 1.56 |
| `leaderboardGetRows` | 1.56 |
| `leaderboardInit` | 1.56 |
| `leaderboardRequestRowsGlobal` | 1.56 |
| `leaderboardRequestRowsGlobalAroundUser` | 1.56 |

#### Localization (5 commands, since 0.50 to 2.04)

| Command | Since |
|---|---|
| `WFSideText` | 0.50 |
| `isLocalized` | 0.50 |
| `localize` | 0.50 |
| `getTextRaw` | 2.2 |
| `diag_localized` | 2.4 |

#### Custom Radio and Chat (8 commands, since 0.50 to 2.00)

| Command | Since |
|---|---|
| `customChat` | 0.50 |
| `customRadio` | 0.50 |
| `radioChannelAdd` | 0.50 |
| `radioChannelCreate` | 0.50 |
| `radioChannelRemove` | 0.50 |
| `radioChannelSetCallSign` | 0.50 |
| `radioChannelSetLabel` | 0.50 |
| `radioChannelInfo` | 2.0 |

#### Radio and Chat (41 commands, since 0.50 to 2.06)

| Command | Since |
|---|---|
| `clearRadio` | 0.50 |
| `commandChat` | 0.50 |
| `commandRadio` | 0.50 |
| `customChat` | 0.50 |
| `customRadio` | 0.50 |
| `directSay` | 0.50 |
| `disableConversation` | 0.50 |
| `enableRadio` | 0.50 |
| `enableSentences` | 0.50 |
| `globalChat` | 0.50 |
| `globalRadio` | 0.50 |
| `groupChat` | 0.50 |
| `groupRadio` | 0.50 |
| `radioChannelAdd` | 0.50 |
| `radioChannelCreate` | 0.50 |
| `radioChannelRemove` | 0.50 |
| `radioChannelSetCallSign` | 0.50 |
| `radioChannelSetLabel` | 0.50 |
| `showChat` | 0.50 |
| `showRadio` | 0.50 |
| `showSubtitles` | 0.50 |
| `shownRadio` | 0.50 |
| `sideChat` | 0.50 |
| `sideRadio` | 0.50 |
| `systemChat` | 0.50 |
| `vehicleChat` | 0.50 |
| `vehicleRadio` | 0.50 |
| `shownChat` | 1.36 |
| `channelEnabled` | 1.42 |
| `currentChannel` | 1.42 |
| `enableChannel` | 1.42 |
| `getPlayerChannel` | 1.42 |
| `setCurrentChannel` | 1.42 |
| `getSubtitleOptions` | 1.94 |
| `getPlayerVoNVolume` | 2.0 |
| `radioChannelInfo` | 2.0 |
| `setPlayerVoNVolume` | 2.0 |
| `conversationDisabled` | 2.6 |
| `radioEnabled` | 2.6 |
| `sentencesEnabled` | 2.6 |
| `shownSubtitles` | 2.6 |

#### Conversations (8 commands, since 0.50)

| Command | Since |
|---|---|
| `kbAddDatabase` | 0.50 |
| `kbAddDatabaseTargets` | 0.50 |
| `kbAddTopic` | 0.50 |
| `kbHasTopic` | 0.50 |
| `kbReact` | 0.50 |
| `kbRemoveTopic` | 0.50 |
| `kbTell` | 0.50 |
| `kbWasSaid` | 0.50 |

### Data and code

#### Arrays (36 commands, since 0.50 to 2.14)

| Command | Since |
|---|---|
| `+` | 0.50 |
| `-` | 0.50 |
| `count` | 0.50 |
| `find` | 0.50 |
| `forEach` | 0.50 |
| `in` | 0.50 |
| `isArray` | 0.50 |
| `resize` | 0.50 |
| `select` | 0.50 |
| `set` | 0.50 |
| `toArray` | 0.50 |
| `toString` | 0.50 |
| `reverse` | 1.24 |
| `pushBack` | 1.26 |
| `deleteAt` | 1.32 |
| `deleteRange` | 1.32 |
| `append` | 1.40 |
| `sort` | 1.44 |
| `arrayIntersect` | 1.48 |
| `param` | 1.48 |
| `params` | 1.48 |
| `isEqualTypeAll` | 1.54 |
| `isEqualTypeArray` | 1.54 |
| `apply` | 1.56 |
| `pushBackUnique` | 1.56 |
| `selectRandom` | 1.56 |
| `selectMax` | 1.66 |
| `selectMin` | 1.66 |
| `parseSimpleArray` | 1.68 |
| `selectRandomWeighted` | 1.76 |
| `findIf` | 1.82 |
| `createHashMapFromArray` | 2.2 |
| `flatten` | 2.2 |
| `insert` | 2.2 |
| `findAny` | 2.10 |
| `forEachReversed` | 2.14 |

#### HashMap (19 commands, since 0.50 to 2.14)

| Command | Since |
|---|---|
| `+` | 0.50 |
| `count` | 0.50 |
| `forEach` | 0.50 |
| `in` | 0.50 |
| `set` | 0.50 |
| `toArray` | 0.50 |
| `deleteAt` | 1.32 |
| `apply` | 1.56 |
| `createHashMap` | 2.2 |
| `createHashMapFromArray` | 2.2 |
| `get` | 2.2 |
| `getOrDefault` | 2.2 |
| `insert` | 2.2 |
| `keys` | 2.2 |
| `merge` | 2.2 |
| `values` | 2.4 |
| `hashValue` | 2.6 |
| `getOrDefaultCall` | 2.12 |
| `createHashMapObject` | 2.14 |

#### Strings (43 commands, since 0.50 to 2.18)

| Command | Since |
|---|---|
| `+` | 0.50 |
| `comment` | 0.50 |
| `compile` | 0.50 |
| `composeText` | 0.50 |
| `copyFromClipboard` | 0.50 |
| `copyToClipboard` | 0.50 |
| `count` | 0.50 |
| `find` | 0.50 |
| `format` | 0.50 |
| `formatText` | 0.50 |
| `hint` | 0.50 |
| `hintC` | 0.50 |
| `hintSilent` | 0.50 |
| `image` | 0.50 |
| `in` | 0.50 |
| `isLocalized` | 0.50 |
| `lineBreak` | 0.50 |
| `localize` | 0.50 |
| `parseNumber` | 0.50 |
| `parseText` | 0.50 |
| `select` | 0.50 |
| `setAttributes` | 0.50 |
| `str` | 0.50 |
| `text` | 0.50 |
| `toArray` | 0.50 |
| `toLower` | 0.50 |
| `toString` | 0.50 |
| `toUpper` | 0.50 |
| `compileFinal` | 0.56 |
| `joinString` | 1.50 |
| `splitString` | 1.50 |
| `toFixed` | 1.66 |
| `parseSimpleArray` | 1.68 |
| `endl` | 1.70 |
| `toLowerANSI` | 1.96 |
| `toUpperANSI` | 1.96 |
| `getTextWidth` | 1.98 |
| `forceUnicode` | 2.2 |
| `insert` | 2.2 |
| `trim` | 2.2 |
| `diag_localized` | 2.4 |
| `fromJSON` | 2.18 |
| `toJSON` | 2.18 |

#### Strings - Regular Expression (3 commands, since 2.06)

| Command | Since |
|---|---|
| `regexFind` | 2.6 |
| `regexMatch` | 2.6 |
| `regexReplace` | 2.6 |

#### Math (40 commands, since 0.50 to 1.92)

| Command | Since |
|---|---|
| `!` | 0.50 |
| `!=` | 0.50 |
| `%` | 0.50 |
| `&&` | 0.50 |
| `*` | 0.50 |
| `+` | 0.50 |
| `-` | 0.50 |
| `/` | 0.50 |
| `<` | 0.50 |
| `<=` | 0.50 |
| `==` | 0.50 |
| `>` | 0.50 |
| `>=` | 0.50 |
| `^` | 0.50 |
| `abs` | 0.50 |
| `and` | 0.50 |
| `ceil` | 0.50 |
| `exp` | 0.50 |
| `false` | 0.50 |
| `finite` | 0.50 |
| `floor` | 0.50 |
| `linearConversion` | 0.50 |
| `ln` | 0.50 |
| `log` | 0.50 |
| `max` | 0.50 |
| `min` | 0.50 |
| `mod` | 0.50 |
| `not` | 0.50 |
| `or` | 0.50 |
| `random` | 0.50 |
| `round` | 0.50 |
| `sqrt` | 0.50 |
| `true` | 0.50 |
| `||` | 0.50 |
| `toFixed` | 1.66 |
| `bezierInterpolation` | 1.92 |
| `decayGraphValues` | 1.92 |
| `getGraphValues` | 1.92 |
| `matrixMultiply` | 1.92 |
| `matrixTranspose` | 1.92 |

#### Math - Vectors (28 commands, since 0.50 to 2.14)

| Command | Since |
|---|---|
| `setVectorDir` | 0.50 |
| `setVectorDirAndUp` | 0.50 |
| `setVectorUp` | 0.50 |
| `vectorDir` | 0.50 |
| `vectorUp` | 0.50 |
| `vectorAdd` | 1.22 |
| `vectorCos` | 1.22 |
| `vectorCrossProduct` | 1.22 |
| `vectorDiff` | 1.22 |
| `vectorDistance` | 1.22 |
| `vectorDistanceSqr` | 1.22 |
| `vectorDotProduct` | 1.22 |
| `vectorMagnitude` | 1.22 |
| `vectorMagnitudeSqr` | 1.22 |
| `vectorMultiply` | 1.22 |
| `vectorFromTo` | 1.26 |
| `vectorNormalized` | 1.26 |
| `vectorDirVisual` | 1.32 |
| `vectorUpVisual` | 1.32 |
| `vectorModelToWorld` | 1.72 |
| `vectorModelToWorldVisual` | 1.72 |
| `vectorWorldToModel` | 1.72 |
| `vectorWorldToModelVisual` | 1.72 |
| `matrixMultiply` | 1.92 |
| `matrixTranspose` | 1.92 |
| `vectorLinearConversion` | 1.92 |
| `vectorSide` | 2.14 |
| `vectorSideVisual` | 2.14 |

#### Math - Geometry (24 commands, since 0.50 to 1.68)

| Command | Since |
|---|---|
| `acos` | 0.50 |
| `asin` | 0.50 |
| `atan` | 0.50 |
| `atan2` | 0.50 |
| `atg` | 0.50 |
| `cos` | 0.50 |
| `deg` | 0.50 |
| `distance` | 0.50 |
| `distanceSqr` | 0.50 |
| `intersect` | 0.50 |
| `lineIntersects` | 0.50 |
| `lineIntersectsWith` | 0.50 |
| `pi` | 0.50 |
| `rad` | 0.50 |
| `sin` | 0.50 |
| `tan` | 0.50 |
| `terrainIntersect` | 0.50 |
| `terrainIntersectASL` | 0.50 |
| `tg` | 0.50 |
| `lineIntersectsObjs` | 1.10 |
| `distance2D` | 1.50 |
| `lineIntersectsSurfaces` | 1.50 |
| `checkVisibility` | 1.56 |
| `terrainIntersectAtASL` | 1.68 |

#### Program Flow (49 commands, since 0.50 to 2.14)

| Command | Since |
|---|---|
| `:` | 0.50 |
| `assert` | 0.50 |
| `breakOut` | 0.50 |
| `breakTo` | 0.50 |
| `call` | 0.50 |
| `case` | 0.50 |
| `catch` | 0.50 |
| `default` | 0.50 |
| `do` | 0.50 |
| `else` | 0.50 |
| `exec` | 0.50 |
| `execFSM` | 0.50 |
| `execVM` | 0.50 |
| `exit` | 0.50 |
| `exitWith` | 0.50 |
| `for` | 0.50 |
| `forEach` | 0.50 |
| `forEachMember` | 0.50 |
| `forEachMemberAgent` | 0.50 |
| `forEachMemberTeam` | 0.50 |
| `from` | 0.50 |
| `goto` | 0.50 |
| `halt` | 0.50 |
| `if` | 0.50 |
| `loadFile` | 0.50 |
| `scopeName` | 0.50 |
| `scriptDone` | 0.50 |
| `scriptName` | 0.50 |
| `sleep` | 0.50 |
| `spawn` | 0.50 |
| `step` | 0.50 |
| `switch` | 0.50 |
| `terminate` | 0.50 |
| `then` | 0.50 |
| `throw` | 0.50 |
| `to` | 0.50 |
| `try` | 0.50 |
| `uiSleep` | 0.50 |
| `waitUntil` | 0.50 |
| `while` | 0.50 |
| `with` | 0.50 |
| `canSuspend` | 1.58 |
| `isUIContext` | 1.76 |
| `break` | 2.2 |
| `breakWith` | 2.2 |
| `continue` | 2.2 |
| `continueWith` | 2.2 |
| `fileExists` | 2.2 |
| `forEachReversed` | 2.14 |

#### Structured Text (11 commands, since 0.50)

| Command | Since |
|---|---|
| `composeText` | 0.50 |
| `ctrlSetStructuredText` | 0.50 |
| `formatText` | 0.50 |
| `hint` | 0.50 |
| `hintC` | 0.50 |
| `hintSilent` | 0.50 |
| `image` | 0.50 |
| `lineBreak` | 0.50 |
| `parseText` | 0.50 |
| `setAttributes` | 0.50 |
| `text` | 0.50 |

#### RTD (46 commands, since 1.34)

| Command | Since |
|---|---|
| `addForceGeneratorRTD` | 1.34 |
| `airDensityCurveRTD` | 1.34 |
| `airDensityRTD` | 1.34 |
| `clearForcesRTD` | 1.34 |
| `collectiveRTD` | 1.34 |
| `difficultyEnabledRTD` | 1.34 |
| `enableAutoStartUpRTD` | 1.34 |
| `enableAutoTrimRTD` | 1.34 |
| `enableStressDamage` | 1.34 |
| `enginesIsOnRTD` | 1.34 |
| `enginesPowerRTD` | 1.34 |
| `enginesRpmRTD` | 1.34 |
| `enginesTorqueRTD` | 1.34 |
| `forceAtPositionRTD` | 1.34 |
| `forceGeneratorRTD` | 1.34 |
| `getEngineTargetRPMRTD` | 1.34 |
| `getRotorBrakeRTD` | 1.34 |
| `getTrimOffsetRTD` | 1.34 |
| `getWingsOrientationRTD` | 1.34 |
| `getWingsPositionRTD` | 1.34 |
| `isAutoStartUpEnabledRTD` | 1.34 |
| `isAutoTrimOnRTD` | 1.34 |
| `isObjectRTD` | 1.34 |
| `isStressDamageEnabled` | 1.34 |
| `numberOfEnginesRTD` | 1.34 |
| `rotorsForcesRTD` | 1.34 |
| `rotorsRpmRTD` | 1.34 |
| `setActualCollectiveRTD` | 1.34 |
| `setBrakesRTD` | 1.34 |
| `setCustomWeightRTD` | 1.34 |
| `setEngineRpmRTD` | 1.34 |
| `setForceGeneratorRTD` | 1.34 |
| `setRotorBrakeRTD` | 1.34 |
| `setWantedRPMRTD` | 1.34 |
| `setWingForceScaleRTD` | 1.34 |
| `stopEngineRTD` | 1.34 |
| `weightRTD` | 1.34 |
| `windRTD` | 1.34 |
| `wingsForcesRTD` | 1.34 |
| `batteryChargeRTD` | n/v |
| `setAPURTD` | n/v |
| `setBatteryChargeRTD` | n/v |
| `setBatteryRTD` | n/v |
| `setStarterRTD` | n/v |
| `setThrottleRTD` | n/v |
| `throttleRTD` | n/v |

#### Animations (28 commands, since 0.50 to 2.18)

| Command | Since |
|---|---|
| `animate` | 0.50 |
| `animateDoor` | 0.50 |
| `animationPhase` | 0.50 |
| `animationState` | 0.50 |
| `doorPhase` | 0.50 |
| `moveTime` | 0.50 |
| `playAction` | 0.50 |
| `playActionNow` | 0.50 |
| `playGesture` | 0.50 |
| `playMove` | 0.50 |
| `playMoveNow` | 0.50 |
| `setFaceAnimation` | 0.50 |
| `switchAction` | 0.50 |
| `switchGesture` | 0.50 |
| `switchMove` | 0.50 |
| `useAudioTimeForMoves` | 0.50 |
| `getAnimAimPrecision` | 1.54 |
| `getAnimSpeedCoef` | 1.54 |
| `setAnimSpeedCoef` | 1.54 |
| `animateSource` | 1.58 |
| `animationNames` | 1.58 |
| `animationSourcePhase` | 1.58 |
| `animateBay` | 1.70 |
| `animatePylon` | 1.70 |
| `elevatePeriscope` | 2.0 |
| `periscopeElevation` | 2.0 |
| `gestureState` | 2.6 |
| `getUnitMovesInfo` | 2.18 |

#### Time (15 commands, since 0.50 to 2.20)

| Command | Since |
|---|---|
| `accTime` | 0.50 |
| `dayTime` | 0.50 |
| `diag_tickTime` | 0.50 |
| `estimatedEndServerTime` | 0.50 |
| `estimatedTimeLeft` | 0.50 |
| `serverTime` | 0.50 |
| `setAccTime` | 0.50 |
| `skipTime` | 0.50 |
| `time` | 0.50 |
| `setTimeMultiplier` | 1.26 |
| `timeMultiplier` | 1.26 |
| `diag_deltaTime` | 1.96 |
| `systemTime` | 2.0 |
| `systemTimeUTC` | 2.0 |
| `uiTime` | 2.20 |

#### Custom Panels (8 commands, since 1.16 to 1.72)

| Command | Since |
|---|---|
| `showUAVFeed` | 1.16 |
| `shownUAVFeed` | 1.16 |
| `enableInfoPanelComponent` | 1.72 |
| `infoPanel` | 1.72 |
| `infoPanelComponentEnabled` | 1.72 |
| `infoPanelComponents` | 1.72 |
| `infoPanels` | 1.72 |
| `setInfoPanel` | 1.72 |

#### Roads and Airports (10 commands, since 0.50 to 2.00)

| Command | Since |
|---|---|
| `airportSide` | 0.50 |
| `assignToAirport` | 0.50 |
| `isOnRoad` | 0.50 |
| `landAt` | 0.50 |
| `nearRoads` | 0.50 |
| `roadsConnectedTo` | 0.50 |
| `setAirportSide` | 0.50 |
| `roadAt` | 1.58 |
| `allAirports` | 1.76 |
| `getRoadInfo` | 2.0 |

#### Vehicle in Vehicle Transport (6 commands, since 1.62)

| Command | Since |
|---|---|
| `canVehicleCargo` | 1.62 |
| `enableVehicleCargo` | 1.62 |
| `getVehicleCargo` | 1.62 |
| `isVehicleCargo` | 1.62 |
| `setVehicleCargo` | 1.62 |
| `vehicleCargoEnabled` | 1.62 |

#### Game 2 Editor (57 commands, since 0.50)

| Command | Since |
|---|---|
| `addEditorObject` | 0.50 |
| `addMenu` | 0.50 |
| `addMenuItem` | 0.50 |
| `allow3DMode` | 0.50 |
| `allowFileOperations` | 0.50 |
| `clearOverlay` | 0.50 |
| `closeOverlay` | 0.50 |
| `collapseObjectTree` | 0.50 |
| `commitOverlay` | 0.50 |
| `createMenu` | 0.50 |
| `deleteEditorObject` | 0.50 |
| `drawLink` | 0.50 |
| `editObject` | 0.50 |
| `editorSetEventHandler` | 0.50 |
| `evalObjectArgument` | 0.50 |
| `execEditorScript` | 0.50 |
| `findEditorObject` | 0.50 |
| `fromEditor` | 0.50 |
| `getEditorCamera` | 0.50 |
| `getEditorMode` | 0.50 |
| `getEditorObjectScope` | 0.50 |
| `getObjectArgument` | 0.50 |
| `getObjectChildren` | 0.50 |
| `getObjectProxy` | 0.50 |
| `importAllGroups` | 0.50 |
| `insertEditorObject` | 0.50 |
| `isRealTime` | 0.50 |
| `isShowing3DIcons` | 0.50 |
| `listObjects` | 0.50 |
| `loadOverlay` | 0.50 |
| `lookAtPos` | 0.50 |
| `moveObjectToEnd` | 0.50 |
| `nMenuItems` | 0.50 |
| `newOverlay` | 0.50 |
| `nextMenuItemIndex` | 0.50 |
| `onDoubleClick` | 0.50 |
| `onShowNewObject` | 0.50 |
| `removeDrawIcon` | 0.50 |
| `removeDrawLinks` | 0.50 |
| `removeMenuItem` | 0.50 |
| `restartEditorCamera` | 0.50 |
| `saveOverlay` | 0.50 |
| `selectEditorObject` | 0.50 |
| `selectedEditorObjects` | 0.50 |
| `setDrawIcon` | 0.50 |
| `setEditorMode` | 0.50 |
| `setEditorObjectScope` | 0.50 |
| `setFromEditor` | 0.50 |
| `setObjectArguments` | 0.50 |
| `setObjectProxy` | 0.50 |
| `setVisibleIfTreeCollapsed` | 0.50 |
| `show3DIcons` | 0.50 |
| `showLegend` | 0.50 |
| `showNewEditorObject` | 0.50 |
| `updateDrawIcon` | 0.50 |
| `updateMenuItem` | 0.50 |
| `updateObjectTree` | 0.50 |

#### Broken Commands (36 commands, since 0.50 to 1.56)

| Command | Since |
|---|---|
| `addPublicVariableEventHandler` | 0.50 |
| `allSites` | 0.50 |
| `camPrepareBank` | 0.50 |
| `camPrepareDir` | 0.50 |
| `camPrepareDive` | 0.50 |
| `camPrepareFovRange` | 0.50 |
| `camSetBank` | 0.50 |
| `camSetDive` | 0.50 |
| `camSetFovRange` | 0.50 |
| `createSite` | 0.50 |
| `createTarget` | 0.50 |
| `debugFSM` | 0.50 |
| `debugLog` | 0.50 |
| `deleteSite` | 0.50 |
| `deleteTarget` | 0.50 |
| `echo` | 0.50 |
| `findCover` | 0.50 |
| `halt` | 0.50 |
| `moveTarget` | 0.50 |
| `setFaceAnimation` | 0.50 |
| `setHideBehind` | 0.50 |
| `setPlayable` | 0.50 |
| `setPosASL2` | 0.50 |
| `setSystemOfUnits` | 0.50 |
| `setVehicleId` | 0.50 |
| `showWarrant` | 0.50 |
| `simulSetHumidity` | 0.50 |
| `textLog` | 0.50 |
| `textLogFormat` | 0.50 |
| `unlockAchievement` | 0.50 |
| `disableDebriefingStats` | 1.0 |
| `getPersonUsedDLCs` | 1.36 |
| `menuShortcutText` | 1.56 |
| `enemy` | n/v |
| `isHideBehindScripted` | n/v |
| `removeClothing` | n/v |

#### Argo (18 commands, since n/v)

| Command | Since |
|---|---|
| `clearKillConfirmations` | n/v |
| `gameValueToJson` | n/v |
| `getCurrentPlayerLevel` | n/v |
| `getLoginStatus` | n/v |
| `getNextId` | n/v |
| `getPlayerCloudId` | n/v |
| `getPlayerLevel` | n/v |
| `isAppSubscribed` | n/v |
| `isPlayerSupporter` | n/v |
| `jsonToGameValue` | n/v |
| `kickPlayer` | n/v |
| `onOfficialServer` | n/v |
| `sendAnalyticEvent` | n/v |
| `sendCloudRequest` | n/v |
| `sendCloudRequestClient` | n/v |
| `sendCloudRequestServer` | n/v |
| `serverConfigTopLevelEntry` | n/v |
| `serverStartMission` | n/v |

#### Performance Profiling (9 commands, since 0.50 to 2.16)

| Command | Since |
|---|---|
| `diag_fps` | 0.50 |
| `diag_fpsMin` | 0.50 |
| `diag_frameNo` | 0.50 |
| `diag_captureFrame` | 1.0 |
| `diag_captureSlowFrame` | 1.0 |
| `diag_captureFrameToFile` | 1.16 |
| `diag_codePerformance` | 1.58 |
| `diag_scope` | 2.2 |
| `diag_testScriptSimpleVM` | 2.16 |

## 5. Key untapped commands worth study

The issue names a set of commands worth a detailed look. Each is verified
below. Some issue entries carry two commands, so the table is longer than the
issue list.

| Command | Since | Group | Note |
|---|---|---|---|
| `checkVisibility` | 1.56 | Math - Geometry | The line-of-sight and visibility query the AI and optics models need. |
| `setUnitTrait` | 1.58 | Object Manipulation | The #78 stamina fix uses the StaminaDrainCoef trait. |
| `isOnRoad` | 0.50 | Roads and Airports | The #117 terrain and traction link. The road-position query. |
| `nearRoads` | 0.50 | Roads and Airports | The nearest-road query. The issue names `nearestRoad`, which does not exist. |
| `getArtilleryETA` | 0.56 | Artillery | Counter-battery and sound ranging (#80). The time to impact. |
| `commandArtilleryFire` | 0.50 | Artillery | Fire-mission control for the artillery model. |
| `setWeaponReloadingTime` | 0.50 | Weapons | Weapon state manipulation. Barrel heat (#130) and ammo temperature (#94). |
| `getAmmoCargo` | 0.56 | Vehicle Inventory | Logistics. The ammo cargo read. |
| `setAmmoCargo` | 0.50 | Vehicle Inventory | Logistics. The ammo cargo write. |
| `remoteExec` | 1.50 | Multiplayer | The #80 sound sync and #116 field sync surface. |
| `nearestObjects` | 0.50 | Object Detection | The #136 local-wind upwind-building query. The #128 anchors. |

## 6. Corrections against issue #147

The issue was written from archived wiki captures. The local DB supersedes it
where the two disagree. Every count in the issue differs from the DB by a
small amount. The DB counts are VERIFIED. The issue counts are **UNKNOWN**
against the local DB. Examples: Object Manipulation 275 against 264, System
89 against 88, Diagnostic 54 against 50, GUI Control 128 against 126, Curator
41 against 44, AI Behaviour 24 against 22.

Four command names in the issue do not exist in the DB:

- **`nearestRoad`** does not exist. The query is `nearRoads`.
- **`stamina`** does not exist. The getter is `getStamina`, the setter is
  `setStamina`. The pair is in the Stamina System group.
- **`groupCombatMode`** does not exist. The getter is `combatMode`. The
  group form is `waypointCombatMode`. The setter is `setCombatMode`.
- **`getModDependencies`** does not exist in the DB. The Mods and Addons
  group holds `isClass` and the config-source reads instead.

Two commands carry a different group in the DB than the issue states:

- **`checkVisibility`** is in **Math - Geometry** in the DB, not Sensors.
- **`setUnitTrait`** is in **Object Manipulation** in the DB, not Unit
  Control.

Four group names in the issue are not DB group labels:

- **Simulation (Objects)** is the **PhysX** group in the DB.
- **Post Processing** is not a group. The `ppEffect` commands are in **Camera
  Control**.
- **Effects** is not a group. The effect commands are in **Sounds** and
  **Particles**.
- **Uncategorised** is not a DB group. Every command carries at least one
  group.

The Regular Expression group is `Strings - Regular Expression` in the DB. It
holds `regexFind`, `regexMatch` and `regexReplace`, all since 2.6. The flag
system in the issue comment comes from the wiki reference page, not from the
command DB. It is **UNKNOWN** against the local DB.

The issue's file list names an absolute path on one machine. This document
does not ship a local path. The inventory is reproduced from the DB instead.

## 7. Sources

- Command DB: acemod/arma3-wiki dist v2.22, `commands/<name>.yml`. Every
  command in this document was read from that DB.
- Related AEE records: [engine-commands-and-features.md](engine-commands-and-features.md),
  [engine-config-surface.md](engine-config-surface.md).
- Sibling command-surface maps: #141 (environment), #144 (geometry,
  simulation, events, AI), #145 (system and diagnostic), #146 (effects,
  post-process, GUI, Eden, Curator, lights).

