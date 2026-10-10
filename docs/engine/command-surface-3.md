# Engine command surface: post-processing, camera, particles, GUI, Eden, Zeus

This is the verified command surface for the presentation and integration
layer. It records the commands the lighting grade (#100), the optics and
starfield overlays (#122), the scalar-field emitters (#116) and the vegetation
fire (#10) depend on. It answers issue #146 and is part three of the
#144-#147 command-surface series.

The document names a command, its group, its introduction version and the one
caveat that changes how AEE must call it. It does not restate the area
narratives in [engine-commands-and-features.md](engine-commands-and-features.md).
Read that document for the engine systems behind the commands, the post-process
parameter arrays and the effect priority model.

## Source and method

- **Source.** The local Arma 3 wiki command DB, acemod/arma3-wiki dist
  **v2.22**. Commands live in `commands/<name>.yml`.
- **Version.** The `since:` block of a page records the introduction version.
  The column-0 `since:` block is the command's own version. A nested, indented
  `since:` block belongs to one alternative syntax or one parameter, not to
  the command. Read the column-0 block. A command that predates the field
  carries no `arma_3` entry, shown here as **n/v** (no version recorded).
- **Config.** Config claims come from the derapified core engine config
  (`bin/config.cpp`), cited by class and line.
- **CBA.** The CBA functions are an addon, not engine commands, so the command
  DB does not hold them. The verified reference is the repo's own usage. A
  count is the number of call sites in `addons/`.
- **Labels.** **VERIFIED** means the value is read from the local DB page, the
  config or the repo. **UNKNOWN** means the source does not carry the claim.
  Nothing here comes from memory.

## 1. Post-processing

| Command | Since | Group | Verified spec | AEE use |
|---|---|---|---|---|
| `ppEffectCreate` | 0.50 | Camera Control | Creates a post-process effect by name and priority. Returns a handle, or -1 on failure. Also takes an array of `[name, priority]` pairs. The page lists the creatable names: RadialBlur, ChromAberration, WetDistortion, ColorCorrections, DynamicBlur, FilmGrain, ColorInversion, SSAO, Resolution. A priority already in use fails creation. | #100: create the colour correction, film grain and blur. |
| `ppEffectAdjust` | 0.50 | Camera Control | Sets the effect parameter array. Local. The handle syntax takes a flat or a packed array. The name syntax needs the packed form, so the packed form is the portable one. | #100: drive the grade from the physics. |
| `ppEffectCommit` | 0.50 | Camera Control | Commits the effect over a duration in seconds. Three syntaxes: effect name, handle, handle array. | Smooth transitions. |
| `ppEffectEnable` | 0.50 | Camera Control | Enables or disables an effect and keeps it alive. The page carries the caveat: "If effect fails to get enabled (can check it with ppEffectEnabled) try adding a little sleep in front of it." | The enable-sleep caveat is the ACE3 nightvision pattern. |
| `ppEffectEnabled` | 1.56 | Camera Control | Reports whether the effect is enabled. | The check the enable caveat names. |
| `ppEffectCommitted` | 0.50 | Camera Control | Reports whether a commit has finished. | Transition gate. |
| `ppEffectForceInNVG` | 0.50 | Camera Control | Forces the effect to render while NVG is active. Local. The page example is `_ppGrain ppEffectForceInNVG true`. | The #100 and #127 gate: make a thermal overlay survive the NVG channel. |
| `ppEffectDestroy` | 0.50 | Camera Control | Frees the effect, by handle or by an array of handles. | Cleanup. |

**The priority-collision caveat (VERIFIED).** The page says a priority already
in use fails creation, and shows a bump-the-priority loop. AEE measured that
the collision returns a positive handle shared with the existing owner on at
least one build ([AEE `addons/lib/functions/fnc_createPPEffect.sqf`]), so a
negative-only return check is not enough. Track every handle the mod owns. The
full measurement is in [engine-commands-and-features.md](engine-commands-and-features.md)
section 1.

## 2. Camera and picture-in-picture

| Command | Since | Group | Verified spec | AEE use |
|---|---|---|---|---|
| `camCreate` | 0.50 | Camera Control | Creates a camera or a seagull at a position, immediately. Objects are created exactly at the given position, without consideration of the surrounding objects. MP: camCreated objects are client-side only. | R2T camera lifecycle (#122). |
| `cameraEffect` | 0.50 | Camera Control | Sets an effect on a camera: `[effectName, effectPosition, r2tName]`. The effect names come from `CfgCameraEffects >> Array`: "Internal", "External", "Fixed", "FixedWithZoom", "Terminate". Needs no `camCommit`. Since 1.74 a single r2t source can be terminated, for example `cam cameraEffect ["terminate", "back", "rtt1"]`. | The #122 r2t camera lifecycle. |
| `cameraEffectEnableHUD` | 0.50 | Camera Control | Enables the in-game UI during a camera effect. The HUD is off by default, which makes a `drawIcon3D` result invisible. | The #122 starfield overlay needs this before any 3D draw. |
| `camCommit` | 0.50 | Camera Control | Commits a camera move over a duration. | Smooth camera interpolation. |
| `camSetPos` | 0.50 | Camera Control | Sets the camera position. | Camera placement. |
| `camSetTarget` | 0.50 | Camera Control | Sets the camera target. | Camera aim. |
| `camDestroy` | 0.50 | Camera Control | Deletes a camera. | Cleanup. Terminate the effect first. |
| `switchCamera` | 0.50 | Camera Control | Switches the view to a vehicle or a camera. | The background-stream workaround for the mix rule below. |
| `setPiPEffect` | 0.50 | Camera Control | Sets a render target's picture-in-picture effect. The first parameter is the render-surface reference from Render To Texture, a String. Then the effect mode and its optional parameters. Modes: 0 normal, 1 NVG, 2 thermal, 3 colour correction `[3, enabled, brightness, contrast, offset, blend, lerp, rgb]`, 7 inverted thermal, 8 green thermal, 9..70 alternate thermal (since 2.10). | PIP optics and the starfield overlay (#122). |

**The mix rule (VERIFIED).** The `cameraEffect` page states: "One cannot mix
and match cameraEffect and can either have multiple r2t cameras or a single
camera for the whole screen." To overlay r2t streams on a background stream,
create an object and use `switchCamera` for the background, then use
`cameraEffect` for the r2t overlay.

## 3. Thermal and night-vision vision

| Command | Since | Group | Verified spec | AEE use |
|---|---|---|---|---|
| `currentVisionMode` | 0.50 | Weapons | Returns the current vision mode of a unit's weapon: 0 normal, 1 night vision, 2 thermal. A unit query returns the unit mode, a vehicle query the driver-seat mode. The alternative syntaxes also return the FLIR index, and take a turret path or a weapon (those forms since 2.8). | The repo reads it to gate the thermal and grade passes ([AEE `addons/vision/functions/vision/fnc_managePostProcess.sqf`]). |
| `setVehicleTIPars` | 0.50 | Object Manipulation | Sets the heat state of a vehicle's engine, wheels and weapon, each 0 (cold) to 1 (hot). Global argument, local effect. Does not work on infantry weapons. | #127 thermal matrix. |
| `setTIParameter` | 2.10 | Environment | Sets a thermal imaging parameter by name, for example "OutputRangeStart". The settings are not saved in a savegame, so reapply them after a load. | #127 thermal tuning. |
| `ppEffectForceInNVG` | 0.50 | Camera Control | See section 1. | The NVG gate (#100, #127). |

**The vision-mode gate (VERIFIED).** The repo calls `currentVisionMode` in the
vision, grade, thermal-display and weather-fx addons, and forces a thermal
overlay into the NVG channel with `ppEffectForceInNVG`
([AEE `addons/thermal_display/functions/fusion/fnc_applyFusionPP.sqf`]).

## 4. Particles

| Command | Since | Group | Verified spec | AEE use |
|---|---|---|---|---|
| `setParticleClass` | 0.50 | Particles | Loads a `CfgCloudlets` class into a particle source. Simple expressions inside the class are not evaluated, which can make a class unusable from script. | The standard particle-source pattern (#116 emitters, #10 fire). |
| `setParticleParams` | 0.50 | Particles | Sets the full ParticleArray. Since 1.11 it overwrites many values set by `setParticleClass`. | Custom particle config. |
| `setParticleRandom` | 0.50 | Particles | Sets the randomisation array: lifeTimeVar, positionVar, moveVelocityVar, rotationVelocityVar, sizeVar, colorVar, directionPeriodVar, directionIntensityVar, angleVar, bounceOnSurfaceVar. angleVar and bounceOnSurfaceVar are optional. bounceOnSurfaceVar since 0.74. | Deterministic against random particle control. |
| `setParticleCircle` | 0.50 | Particles | Creates particles in a circle of a given radius, with a circle velocity. The optional third element `ignoreSurfaces` (since 2.22) calculates the position relative to the source instead of the nearest surface. | Circular emission patterns. |
| `setParticleFire` | 1.8 | Particles | Sets the fire parameters: coreIntensity (damage in the centre of fire), coreDistance (how far a unit can take damage), damageTime (how often a unit takes damage). | Fire damage from the particle (#10). |
| `setDropInterval` | 0.50 | Particles | Sets the emission interval. The engine caps the particle count at 18000. | Emission rate. |
| `drop` | 0.50 | Particles | Creates a one-shot particle effect from a ParticleArray. The particles are single polygons that always face the player. | One-shot effects. |

**The particle-source pattern (VERIFIED).** The `setParticleClass` page uses
the exact form:

```sqf
_source = "#particlesource" createVehicleLocal _pos;
_source setParticleClass "ObjectDestructionFire1Smallx";
```

`setParticleFire` carries the damage channel, so a fire particle can damage a
unit. The config base classes are `CfgCloudlets >> Default` and
`CfgCloudlets >> Explosion` (`bin/config.cpp:3585`; 23 classes).

## 5. GUI and drawing

| Command | Since | Group | Verified spec | AEE use |
|---|---|---|---|---|
| `createDisplay` | 0.50 | GUI Control | Creates a child display from a resource name. The player can move while it is shown, unlike `createDialog`. It takes the mouse pointer and closes on Esc. Since 1.50 it returns the Display and looks in `description.ext` before the main config. | The non-blocking in-game HUD (#97). |
| `createDialog` | 0.50 | GUI Control | Creates a modal dialog from a class name. It returns true on success, or a Display with the optional `forceOnTop` (since 2.8). | Settings dialogs. |
| `ctrlCreate` | 1.26 | GUI Control | Creates a control in a display: `[class, idc, controlsGroup]`. The controlsGroup is optional. The class may be from the main config or the mission config (mission config since 1.70). | Dynamic UI. |
| `drawIcon` | 0.50 | GUI Control - Map | Draws an icon on the map: `[texture, color, position, width, height, angle, text, shadow, textSize, font, align]`. It must run every frame, so use the `onDraw` handler. textSize, font and align since 0.72. | Map overlays (#122 starfield, weather markers). |
| `drawLine` | 0.50 | GUI Control - Map | Draws a line on the map: `[from, to, color, width]`. The page caveat: "Can decrease framerate!" width since 2.18. | The perf caveat for #122: throttle the draw calls. |
| `drawRectangle` | 0.50 | GUI Control - Map | Draws a rectangle on the map: `[centre, halfWidth, halfHeight, angle, color, fill, alignWithMap]`. alignWithMap since 2.18. | Zone overlays (#116 plume bounds). |
| `drawPolygon` | 1.58 | GUI Control - Map | Draws a polygon on the map: `[polygon, color]`. It cannot fill the polygon with colour. Use `drawTriangle` to fill. | Plume footprints. |
| `displayAddEventHandler` | 0.50 | GUI Control - Event Handlers, Event Handlers | Adds an event handler to a display and returns its index, or -1 on failure. Display handlers run last to first added, so an input override belongs in the first added handler. The "on" prefix is removed from the event name. | UI event hooks, including the `onDraw` frame driver. |

**The framerate caveat (VERIFIED).** `drawLine` "can decrease framerate". The
#122 starfield overlay and the #116 plume rendering must throttle their draw
calls, for example to 1 Hz, instead of drawing every frame. The icon and line
draws are UI-layer and cannot be occluded by world geometry.

## 6. Eden editor

| Command | Since | Group | Verified spec | AEE use |
|---|---|---|---|---|
| `create3DENEntity` | 1.56 | Eden Editor | Creates an Eden entity: `[mode, class, position, isEmpty]`. Modes: "Object", "Trigger", "Waypoint", "Logic", "Marker", "Comment" (Comment since 2.14). isEmpty makes a vehicle without crew. This is the only way to add an editable entity: `createVehicle` and `createUnit` still work but the result is not editable. | Editor tooling: module placement automation. |
| `get3DENSelected` | 1.56 | Eden Editor | Returns the selected Eden entities of a type. A wrong type returns `[[], [], [], [], [], []]` and shows an error. | Editor selection read. |
| `set3DENAttributes` | 1.56 | Eden Editor | Sets entity attributes in a batch: `[[entities, class, value], ...]`. Attributes exist only inside the Eden workspace, not in preview or an exported scenario. | Editor automation. |
| `get3DENConnections` | 1.56 | Eden Editor | Returns the connections on an entity, as a class from `Cfg3DEN >> Connections`. | Module wiring. |

**UNKNOWN against the config read here.** `Cfg3DEN` is not in the derapified
core engine config (`bin/config.cpp`). The Eden config lives in the Eden
editor's own config, which this document did not read. Treat the `Cfg3DEN`
class structure as UNKNOWN.

## 7. Zeus (Curator)

| Command | Since | Group | Verified spec | AEE use |
|---|---|---|---|---|
| `addCuratorEditableObjects` | 1.16 | Curator | Registers objects a curator can edit: `[objects, addCrew]`. | Make AEE-created objects Zeus-editable (#116 emitters, #19 craters). |
| `curatorEditableObjects` | 1.16 | Curator | Returns all editable objects of a curator. Global. | The Zeus object list. |
| `curatorMouseOver` | 1.16 | Curator | Returns the curator editable object under the pointer: `[""]` if none, `[typeName, object]` if one. Local. | Zeus-aware interactions. |
| `setCuratorCoef` | 1.16 | Curator | Sets the coefficient of a curator action. A coefficient below -1000000 disables the action. | Zeus cost tuning. |

**UNKNOWN against the local DB.** The issue claims `curatorMouseOver` returns
`[]` when not in curator mode. The page does not state that case. The issue
lists the `setCuratorCoef` actions "Place", "Edit", "Delete", "Destroy",
"Group", "Synchronize". The page enumerates no action list. Only "Place" and
"Delete" appear, in the examples. Treat the full action list as UNKNOWN.

## 8. CBA (the mod's foundation)

The mod builds on the Community Base Addons framework. The CBA functions are
not engine commands, so the command DB does not hold them. The verified
reference is the repo's own usage. A count is the number of call sites in
`addons/`.

| Function | Uses | Verified role | AEE use |
|---|---|---|---|
| `CBA_fnc_addSetting` | 81 | Registers a CBA setting. | The initSettings pattern. |
| `CBA_fnc_addPerFrameHandler` | 60 | Registers a per-frame handler. | The tick loop. |
| `CBA_fnc_removePerFrameHandler` | 10 | Removes a per-frame handler. | Tick teardown. |
| `CBA_fnc_addKeybind` | 8 | Registers a keybind. | Input. |
| `CBA_fnc_addEventHandler` | 4 | Registers a CBA event handler. | The AEE event surface. |
| `CBA_fnc_addPlayerEventHandler` | 4 | Registers a player event handler. | Player-state hooks. |
| `CBA_fnc_addClassEventHandler` | 3 | Registers a class-wide engine event handler. | The raw engine event hooks. |
| `CBA_fnc_getFov` | 2 | Returns the field of view. | Optics. |
| `CBA_fnc_localEvent` | 1 | Raises a local CBA event. | The `AEE_WeatherUpdated` event ([AEE `addons/core/functions/fnc_updateEnvironment.sqf`]). |
| `CBA_fnc_execNextFrame` | 1 | Runs code on the next frame. | Deferred execution. |

## 9. Corrections against issue #146

1. **`setParticleCircle` has a third element.** The issue gives two elements,
   `[circleRadius, circleVelocity]`. The DB syntax has an optional third
   element `ignoreSurfaces` (since 2.22).
2. **`curatorMouseOver` not-in-curator case is UNKNOWN.** The issue claims
   `[]`. The DB page does not state that case.
3. **`setCuratorCoef` action list is UNKNOWN.** The issue lists six actions.
   The DB enumerates none, and only "Place" and "Delete" appear in the
   examples.
4. **`setParticleClass` class name.** The issue writes the class as
   `"CfgCloudletsClass"`, a placeholder. The DB example uses a real class
   name. No defect, but the placeholder is not a class.
5. **CBA names that do not appear in the repo.** The issue lists
   `CBA_fnc_globalEvent`, `CBA_fnc_hash`, `CBA_fnc_compileFinal` and
   `CBA_fnc_callNextFrame`. None of the four names appears in `addons/`. The
   deferred-execution function the repo uses is `CBA_fnc_execNextFrame`, not
   `CBA_fnc_callNextFrame`. The event the repo raises is `CBA_fnc_localEvent`.
   No `CBA_fnc_globalEvent` call exists.

The following issue claims are VERIFIED: the `setPiPEffect` first parameter is
the R2T render-surface reference; the `cameraEffect` mix rule; the
`ppEffectEnable` enable-sleep caveat; the `ppEffectForceInNVG` example
`_ppGrain ppEffectForceInNVG true`; the `drawLine` "can decrease framerate"
caveat; the `createDisplay` move-while-shown behaviour.

## Sources

- Command DB: acemod/arma3-wiki dist v2.22. Commands read from
  `commands/<name>.yml`: `ppEffectCreate`, `ppEffectAdjust`, `ppEffectCommit`,
  `ppEffectEnable`, `ppEffectEnabled`, `ppEffectCommitted`,
  `ppEffectForceInNVG`, `ppEffectDestroy`, `camCreate`, `cameraEffect`,
  `cameraEffectEnableHUD`, `camCommit`, `camSetPos`, `camSetTarget`,
  `camDestroy`, `switchCamera`, `setPiPEffect`, `currentVisionMode`,
  `setVehicleTIPars`, `setTIParameter`, `setParticleClass`,
  `setParticleParams`, `setParticleRandom`, `setParticleCircle`,
  `setParticleFire`, `setDropInterval`, `drop`, `particlesQuality`,
  `createDisplay`, `createDialog`, `ctrlCreate`, `drawIcon`, `drawLine`,
  `drawRectangle`, `drawPolygon`, `displayAddEventHandler`,
  `create3DENEntity`, `get3DENSelected`, `set3DENAttributes`,
  `get3DENConnections`, `addCuratorEditableObjects`, `curatorEditableObjects`,
  `curatorMouseOver`, `setCuratorCoef`.
- Vanilla config: the derapified core engine config (`bin/config.cpp`):
  `CfgCurator`:842, `CfgCloudlets`:3585, `CfgCameraEffects`:14724.
- AEE (read-only): `addons/lib/functions/fnc_createPPEffect.sqf`,
  `addons/vision/functions/vision/fnc_managePostProcess.sqf`,
  `addons/thermal_display/functions/fusion/fnc_applyFusionPP.sqf`,
  `addons/core/functions/fnc_updateEnvironment.sqf`.
- Related engine records: [command-surface.md](command-surface.md) (the #144
  inventory), [engine-commands-and-features.md](engine-commands-and-features.md)
  (the area narratives and the post-process parameter arrays).
