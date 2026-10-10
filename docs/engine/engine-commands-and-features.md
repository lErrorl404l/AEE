# Arma 3 Engine: Commands and Features Reference

Purpose: a source-backed reference for the domains AEE touches, so AEE stops
guessing what the engine can do. Covers the SQF commands, the engine systems
behind them, and the ceilings a mod cannot cross.

Scope: atmosphere and weather, ballistics, thermal and optics, night vision,
physiology, mobility, armour, material, maritime, radio, AI, wildlife, effects,
environmental, and the map and symbology.

## How to read this

- Part 1 lists commands by job. Each entry gives what the command does and its
  limits or gotchas. The gotchas are the point.
- Part 2 describes the engine systems and what they do and do not allow.
- Part 3 is the consolidated ceiling list: what a mod cannot do, with evidence.
- Part 4 records the sources and the BIKI access problem.
- The complete command inventory, every group with its command count and its
  Arma 3 version, is in
  [engine-command-inventory.md](engine-command-inventory.md).

## Source hierarchy and method

1. The BIKI (Bohemia Interactive Community Wiki) is the written source. The live
   wiki returns HTTP 403 from Cloudflare to a direct fetch. Every BIKI citation
   in this document was read through the Wayback Machine:
   `https://web.archive.org/web/2024/https://community.bistudio.com/wiki/<Page>`.
   Wayback rate-limits (HTTP 429); fetches were spaced.
2. The structured command database is acemod/arma3-wiki, `dist` branch, data
   version 2.22 (`https://github.com/acemod/arma3-wiki`). It holds 2695 command
   definitions with syntax, group, multiplayer note, and the "since" version.
   It was cloned and parsed. Its descriptions already carry many documented
   limits, which are quoted here as "the DB says".
3. Ground truth is the shipped engine content: the unpacked scripts under
   `functions_f` (1139 SQF), and the module and data PBOs. Where the BIKI is
   thin, the shipped script is quoted.
4. The open-sourced RV/Poseidon engine
   (`https://github.com/BohemiaInteractive/CWR`) is the Arma ancestor and the
   only readable engine source. It is cited where it settles a question.

The shipped content read for this reference: the Arma 3 install `Addons/`
and the unpacked engine PBOs.

Notation: "engine source proves" means the open-sourced engine or a shipped
`config.cpp` shows it. "community-reported" means a forum or mod source, not
the vendor. "UNKNOWN" means nothing supports a claim.

## The BIKI access problem (what was read instead)

- `https://community.bistudio.com/wiki/<Page>` returns **HTTP 403**, Cloudflare
  "Just a moment...". The live wiki is not machine-readable.
- Workaround: Wayback Machine snapshots. `https://web.archive.org/web/2024/...`
  returned full page HTML for `setAperture`, `drawLine`, `drawIcon`,
  `skipTime`, `setTimeMultiplier`, and others.
- Some pages were never archived (for example `RscMapControl` has no CDX
  snapshot). For those, the shipped `config.cpp` and the open-sourced Poseidon
  `UIMap.cpp` were read instead.
- The acemod command DB substitutes for the per-command wiki pages at scale.

<!-- SECTIONS: command and feature sections are appended below by the assembly. -->

## Part 1 — Commands, grouped

The commands are grouped as requested. Each group names the area section that
details it. The twelve requested groups come first, then the domain groups AEE
also touches. The area sections are in Part 2.

| Requested group | Covered in |
|---|---|
| Config and class system | Network and config, §4 |
| Simulation and scheduling | Simulation, §1–2 |
| Rendering and post-process | Rendering, §1–2 |
| Camera | Rendering, §3–4 |
| Time and weather | World, §1–2 |
| Map and markers | World, §3–4 |
| Sounds | World, §5 |
| Particles | Rendering, §5 |
| Animation | Simulation, §3 |
| Network and JIP | Network and config, §1–3 |
| Files and IO | Network and config, §6 |
| Diagnostics | Network and config, §7 |
| AI | Domains, §1 |
| Mobility | Domains, §2 |
| Physiology | Domains, §3 |
| Armour, hit points, material, surfaces | Domains, §4 |
| Radio | Domains, §5 |
| Wildlife and agents | Domains, §6 |
| Maritime | Domains, §7 |
| Effects and environmental sound | Domains, §8 |

## Part 2 — Commands and engine systems, by area

Each area gives the commands and the engine system behind them, with limits
and gotchas, and closes with that area's ceilings. Part 3 consolidates them.

## Section: rendering, post-process, camera, particles, optics

Engine reference for AEE. Evidence keys: **[DB]** = acemod/arma3-wiki command DB
v2.22 (`the acemod database entry <name>.yml`, parsed
`the parsed command database`). **[WIKI]** = BIKI page via
`web.archive.org/web/2024/`. **[CFG]** = derapified vanilla config
(`the derapified core engine config (Dta/bin.pbo)`, `the derapified map_altis.pbo config`).
**[AEE]** = observed in the AEE repo. Every claim below carries one of these.

### 1. Post-process effect system

**What it is.** A stack of full-screen GPU effects applied after the scene
render, before the HUD. Script controls the stack only; it cannot add a new
effect type or a custom shader.

**Lifecycle [DB].**

| Command | Line |
|---|---|
| `ppEffectCreate [name, priority]` | Handle, or -1 on failure. Also takes an array of `[name, priority]` pairs. |
| `ppEffectAdjust handle [params]` | Set the effect parameter array. Local. |
| `ppEffectCommit handle duration` | Commit over `duration` seconds. Also takes a handle array. |
| `ppEffectEnable handle bool` | On/off, keeps the effect alive. |
| `ppEffectEnabled handle` | Is it enabled. |
| `ppEffectCommitted handle` | Has a commit finished. |
| `ppEffectForceInNVG handle bool` | Draw the effect while NVG is active. |
| `ppEffectDestroy handle` | Free the effect. Also takes a handle array. |

**Priority model — and a documented defect [WIKI] vs [AEE].** The priority sets
apply order, higher applied later (on top). Base priorities: ColorInversion
2500, FilmGrain 2000, ColorCorrections 1500, DynamicBlur 400, WetDistortion 300,
ChromAberration 200, RadialBlur 100, SSAO 0, Resolution 0. BIKI says "if there is
another effect using the same priority, creation will fail", and shows a
bump-the-priority loop. **Measured in AEE, this is wrong on at least one build
[AEE `addons/lib/functions/fnc_createPPEffect.sqf`]:** `ppEffectCreate` at an
occupied priority returned a **POSITIVE** handle shared with the existing owner
(RPT: `optics/FilmGrain handle=32 priority=2000` and
`nightvision/FilmGrain handle=32 priority=2000`). So a negative-only return check
is dead code for the collision case, and two modules can silently own one
handle. AEE bumps and compares every candidate handle against every handle it
already owns. Treat the BIKI wording as unverified; the safe pattern is to
track your own handles.

**Effect parameter model [WIKI].**

- **RadialBlur** `[powerX, powerY, offsetX, offsetY]`, defaults
  `[0.01,0.01,0.06,0.06]`. Does nothing if RADIAL BLUR is off in Video Options.
- **ChromAberration** `[aberrationPowerX, aberrationPowerY, aspectCorrection]`,
  defaults `[0.005,0.005,false]`.
- **WetDistortion** 16 params, no commit needed, auto-cancels under water.
- **ColorCorrections** `[brightness, contrast, offset, [blendRGBA],
  [colorizeRGBA], [weightRGB,0], [radial 7-param]]`. The radial 7th tuple
  (Arma 3) is `[radiusMajor, radiusMinor, rotationDeg, centerX, centerY,
  innerCoef, interpCoef]`; ranges `0..1, 0..1, 0..359, -1..1, -1..1, 0..1, 0...`.
  brightness 0..2, contrast 1 = normal.
- **DynamicBlur** `[value]`, default `[0]`.
- **FilmGrain** `[intensity, sharpness, grainSize, intensityX0, intensityX1,
  monochromatic]`, defaults `[0.005,1.25,2.01,0.75,1.0,0]`. Monochromatic is
  numeric in Arma 3 (0 = mono, any other = colour).
- **ColorInversion** `[R, G, B]`, defaults `[0,0,0]`.
- **SSAO** 11 params, defaults all 0.
- **Resolution** `[verticalResolution]`; negative resets, clamps to the render
  height. Base priority 0.

**Advanced effects — not creatable [WIKI].** `LightShafts` and `HBAOPlus` cannot
be made with `ppEffectCreate`. `LightShafts` is addressed by name
(`"LightShafts" ppEffectAdjust [sunInner, sunOuter, exposure, decay]`) and
adjusts immediately without commit. **Ceiling:** a mod cannot insert a custom
effect type into the stack.

**ppEffectForceInNVG [DB].** Forces an effect to render inside NVG. AEE uses the
flag to make a thermal overlay survive the NVG channel
([AEE `addons/vision/functions/vision/fnc_runThermalPass.sqf`]).

**DepthOfField is a real ppEffect, unlisted [AEE].** The BIKI effect list omits
it, but `ppEffectCreate ["DepthOfField", priority]` returns a live handle and
AEE uses it for the NVG objective focus
([AEE `addons/nightvision/functions/fnc_applyNVGTubeModel.sqf:1178`]). AEE treats
it as enhancement-only: if creation fails the build, NVG DoF is disabled rather
than leaving a permanent -1 handle. `camSetFocus` is camera-only and does not
replace it. **This is community/observed, not a documented effect** — verify per
build.

### 2. Exposure: HDR, aperture, eye adaptation

**The command pair [DB]/[WIKI].**

- `setAperture value` — eye accommodation aperture. `value <= 0` = automatic.
  Maximum value with an effect is about 100. **Higher = darker** (f-number
  metaphor): 50 = daylight outdoor, 30 = daylight indoor, below 20 = very bright
  night (BIKI note, Namikaze 2009). Local.
- `setApertureNew [minimum, standard, maximum, luminance]` — HDR aperture range.
  `setApertureNew [-1]` resets to default.
- **Interplay [WIKI]:** with HDR enabled (default), `setAperture v` *also forces*
  `setApertureNew [v, v, v, 1]`. To set a range, run `setApertureNew` **after**
  `setAperture`. This is a real gotcha and easy to miss.
- **Both reset at mission start [WIKI]/[AEE].** A value set before the mission
  resets as if never set. Use `sleep 0.1` or a post-init driver.
- **HDR requirement [WIKI]:** `setApertureNew` has effect only when HDR is on.

**Engine HDR config [CFG].** `CfgWorlds >> CAWorld >> HDRNewPars`
(vanilla Altis `map_altis_extract/config.cpp:473`; engine default
`bin_raw/bin/config.cpp:16928`). Keys a mod can override: `minAperture`,
`maxAperture`, `apertureRatioMax/Min`, the `bloom*` and `tonemap*` families,
`nvgApertureMin/Standard/Max`, `nvgStandardAvgLum`, `nvgLightGain`,
`nvgTransition*`, `nightShift*`, `eyeAdaptFactorLight`, `eyeAdaptFactorDark`.
Altis values: `minAperture=0.00001`, `maxAperture=256`,
`eyeAdaptFactorLight=3.3`, `eyeAdaptFactorDark=0.75`,
`nightShiftMaxAperture=0.002`, `nvgApertureMin/Std/Max=10/12.5/16.5`,
`nvgLightGain=320`. The engine default differs (`nvg* = 1/7/15`,
`nvgLightGain=100`, `tonemapMethod=2` vs Altis 1). AEE restates the full block
in `addons/lighting/config.cpp` and locks `nvgApertureMin=Standard=Max=7`
to remove the artificial NVG range.

**Depth-of-field config [CFG].** `CfgWorlds >> CAWorld >> DOFPars`
(`bin_raw/bin/config.cpp:16970`): `focusDistance`, `blur`, `farOnly`, plus water
and water-goggles variants. AEE sets `focusDistance=12, blur=0.6, farOnly=1`.

**`apertureParams` [AEE].** `apertureParams` returns the engine's own estimated
luminance and a "blinding" term (element 9, no documented unit)
([AEE `addons/eye/functions/eye/fnc_eyeSampleScene.sqf`,
`fnc_eyeLocalLux.sqf`]). AEE reads it and pins `setApertureNew` every frame so
AEE owns the adaptation rate, not the engine. **Ceiling:** the engine's own
adaptation rate is fixed by `eyeAdaptFactorLight/Dark`; a script can only
override the resulting aperture, not the internal luminance estimate.

### 3. Camera, thermal, picture-in-picture

**Camera commands [DB].**

- `camCreate [type, pos]` — create a camera or seagull immediately. `type` is
  usually `"camera"`. **MP:** camCreated objects are client-side only.
- `cameraEffect [effectName, position, r2tName]` — set an effect on the camera.
  Types: `"Internal"`, `"External"`, `"Fixed"`, `"FixedWithZoom"`,
  `"Terminate"`. Needs no `camCommit`. **Gotcha:** you cannot mix a full-screen
  camera with multiple r2t cameras; the docs give a workaround (switchCamera for
  the background + cameraEffect for the r2t overlay). Since 1.74 you can
  terminate a single r2t source.
- `cameraEffectEnableHUD bool` — **the HUD is OFF by default during a camera
  effect**, so `drawIcon3D` is invisible until you enable it.
- `camSetPos` / `camSetTarget` + `camCommit time` — smooth interpolation; `time
  0` is immediate.
- `camDestroy` — does **not** terminate the effect automatically; call
  `cameraEffect ["terminate", ...]` first.
- `switchCamera target` — modes `"INTERNAL"`, `"GUNNER"`, `"EXTERNAL"`,
  `"GROUP"`, `"CARGO"`. Does not give control; use `remoteControl`. Always
  switchCamera before remoteControl.
- `cameraView` (returns mode), `cameraOn` (vehicle the camera is on).
- `camUseNVG bool` — force NVG on the camera.
- `setPiPEffect [effect, ...]` — the render-to-texture (PiP) effect. Mode 0 =
  normal, 1 = NVG, 2 = thermal, 3 = colour correction (with its own 8-param
  array), 7/8 = alt thermal (inverted/green), 9..70 = alt thermal variants
  (since 2.10). **Ceiling:** the thermal palette set is engine-fixed (WHOT/BHOT
  family); a mod selects a mode, it cannot author a palette.

**Thermal/NV pipeline [AEE].** `currentVisionMode` returns 0 = normal, 1 = NVG,
2 = thermal. AEE drives both an engine thermal channel (mode 2) and a day
channel (mode 0 with native TI disabled) through one pass; the only host
difference is the `ppEffectForceInNVG` flag
([AEE `addons/vision/functions/vision/fnc_runThermalPass.sqf`]). **Ceiling:** the
engine thermal model is not replaceable; AEE overlays a `ppEffect`-based
rendition and reads `apertureParams`, it does not change the engine's own
radiance solver.

### 4. Lighting

**Commands [DB].** `setLightColor` (diffuse, front faces), `setLightAmbient`
(back faces), `setLightIntensity` (direct), `setLightBrightness` (legacy;
`Intensity = Brightness^2 * 2500`; the docs say avoid it), `setLightAttenuation
[start, constant, linear, quadratic, ...]`, `setLightUseFlare`,
`setLightFlareSize`, `setLightFlareMaxDistance`, `setLightConePars`,
`setLightDayLight`. Locality is local.

**Config [CFG].** `CfgLights` (`bin_raw/bin/config.cpp:4225`) holds only
`ObjectDestructionLight` and `ExplosionLight`. Light source objects are declared
per-vehicle (`CfgVehicles >> lightPoints` families); the light commands act on a
`light` object created by the vehicle or `createVehicle`.

**Gotcha [AEE].** AEE drives dynamic star and meteor lights with
`setLightUseFlare` + `setLightFlareSize` + `setLightFlareMaxDistance` + a
non-black colour, and keeps `setLightAmbient` black so the field stays dark
([AEE `addons/lighting/functions/astronomy/fnc_starLightsSync.sqf`]). The
flare path is BIKI "Light Source Tutorial"-derived, community-reported.

### 5. Particles

**Commands [DB].** `setParticleParams`, `setParticleRandom`, `setParticleCircle`,
`setParticleClass`, `setParticleFire`, `drop`, `particlesQuality`,
`setParticleClass`.

- `setParticleClass source "ClassName"` — load a `CfgCloudlets` class.
  **Gotcha:** simple expressions inside the config class are NOT evaluated, so
  some vanilla classes are unusable from script.
- `setParticleParams source [ParticleArray]` — the full 24-element array. Order:
  0 shapeName (string or `[p3d, divisor, row, count, loop]`), 1 animationName
  (must be empty; a value throws "Skeletal animation not supported"), 2 type
  ("Billboard" or "SpaceObject"), 3 timerPeriod, 4 lifetime, 5 position,
  6 moveVelocity, 7 rotationVelocity, 8 weight, 9 volume, 10 rubbing (wind),
  11 size (array over lifetime, m), 12 colour (array of RGBA over lifetime),
  13 animationPhase, 14 randomDirectionPeriod, 15 randomDirectionIntensity,
  16 onTimer, 17 beforeDestroy, 18 object, 19 angle, 20 onSurface, 21
  bounceOnSurface, 22 emissiveColor ([WIKI] ParticleArray).
- `setParticleRandom source [lifeTimeVar, positionVar, moveVelocityVar,
  rotationVelocityVar, sizeVar, colorVar, directionPeriodVar,
  directionIntensityVar, angleVar, bounceOnSurfaceVar]` — 10 elements.
- `setParticleCircle source [radius, velocityVector, ignoreSurfaces]` —
  `ignoreSurfaces` since 2.22.
- `setParticleFire source [coreIntensity, coreDistance, damageTime]` — Arma 3
  1.8.
- `drop [params]` — one-shot `ParticleArray`, global arg / local effect.

**Config [CFG].** `CfgCloudlets` (`bin_raw/bin/config.cpp:3585`) — base classes
`Default`, `Explosion`, `Table`-driven colour keyframes. **Ceiling:** particle
params are expensive per particle; `bounceOnSurface` "has a significant impact
on performance" [WIKI]. Particle count is capped by the user's `particlesQuality`
setting (0/1/2), so a mod's effect density is not guaranteed on every client.

### 6. HUD / 3D overlay draw

**Commands [DB].** `drawIcon3D`, `drawLine3D`, `drawRectangle` (map),
`drawArrow` (map), plus `drawIcon`/`setDrawIcon`/`updateDrawIcon`/`removeDrawIcon`.

- `drawIcon3D` **must run every frame** — use the `Draw3D` mission event handler.
  Invisible through a custom camera unless `cameraEffectEnableHUD true`.
  `showHUD false` hides it. Use the `*Visual` position variants
  (`getPosASLVisual`) to avoid flicker. `width`/`height` are multipliers of
  `CfgInGameUI >> Cursor >> activeWidth/activeHeight`, not screen units.
  Since 2.22 it also takes a HashMap icon.
- `drawLine3D [start, end, colour, width]` — current frame only, `Draw3D`.
- `drawRectangle`/`drawArrow` draw on the map and need `onDraw` each frame.

**Ceiling:** these draw into the UI layer; they are always-on-top and cannot be
occluded by world geometry.

### 7. Object material / texture / scale

**Commands [DB].** `setObjectMaterial obj [index, materialPath]` (local;
`"#reset"` since 2.20), `setObjectMaterialGlobal` (global, 1.54),
`setObjectTexture obj [index, path]` (local), `setObjectTextureGlobal`
(global, JIP-compatible), `setObjectScale object scale`.

- Textures must be a power of two on each axis; max 4096x4096; formats .pac,
  .paa, .jpg, .jpeg, .ogg, .ogv. Selection index or hidden-selection name;
  `"#reset"` since 2.20.
- `setObjectScale` range 0.0001..65504. **Gotchas:** works only on attached
  objects or Simple Objects; LOD limits still apply (walkable surfaces ~70 m,
  collision limited from centre); a direction change (`setDir`, `setVectorDir`)
  **resets the scale to 1**, so set direction first; Eden edits do not save.
- `createSimpleObject [shapeName, posWorld, local]` — decorative object from a
  .p3d. Supported: collision, texturing (syntax 2 / class name), animation,
  penetration. **Unsupported: PhysX, damage, AI pathfinding (AI walks through
  walls), built-in lights.** `addAction` does not work; syntax-1 objects cannot
  be textured. `setVariable`/`getVariable` since 1.68.

**Ceiling:** no custom shader or per-object material program. Materials and
textures are selected from existing `.rvmat`/`.paa` assets only.

### 8. What a mod cannot do here (ceilings, with evidence)

- **No custom post-process effect type or custom shader** — `ppEffectCreate`
  accepts only the fixed list [WIKI]; the stack has no script-insertable stage.
- **No control of post-process apply order** beyond the priority integer.
- **Aperture direction is fixed** — higher is darker; a mod cannot invert it
  [WIKI].
- **Thermal palette is engine-fixed** — `setPiPEffect` selects a mode, it does
  not author a palette [WIKI setPiPEffect].
- **Thermal radiance model is engine-internal** — a script overlays a
  ppEffect-based rendition [AEE `fnc_runThermalPass.sqf`].
- **Particles are capped by the client's `particlesQuality`** [DB].
- **`drawIcon3D` and the 3D draws are UI-layer, not world-occluded** [DB].

### Sources

- Command DB: `the acemod database commands/*.yml` (acemod/arma3-wiki dist
  v2.22). Pages used: ppEffectCreate, ppEffectAdjust, ppEffectCommit,
  ppEffectEnable, ppEffectDestroy, ppEffectForceInNVG, setAperture,
  setApertureNew, setPiPEffect, cameraEffect, cameraEffectEnableHUD, camCreate,
  camSetPos, camSetTarget, camCommit, camDestroy, switchCamera, cameraView,
  cameraOn, setObjectMaterial(Global), setObjectTexture(Global), setObjectScale,
  setLight*, drawIcon3D, drawLine3D, drawRectangle, drawArrow, setParticle*,
  drop, createSimpleObject, particlesQuality.
- BIKI via Wayback 2024:
  `https://web.archive.org/web/2024/https://community.bistudio.com/wiki/Post_Process_Effects`,
  `.../wiki/ParticleArray`, `.../wiki/setAperture`. Cached locally as
  `the post-process wiki mirror`, `wb_particle.html`, `wb_setaperture.html`.
- Vanilla config: `the derapified core engine config (Dta/bin.pbo)` (CfgCloudlets:3585,
  CfgLights:4225, HDRNewPars:16928, NVGPars:16959, DOFPars:16970,
  CfgCameraEffects:14724); `the derapified map_altis.pbo config`
  (HDRNewPars:473, Lighting:510).
- AEE (read-only): `addons/lib/functions/fnc_createPPEffect.sqf`,
  `addons/eye/functions/eye/fnc_eyeAperture.sqf`,
  `addons/eye/functions/eye/fnc_eyeSampleScene.sqf`,
  `addons/vision/functions/vision/fnc_runThermalPass.sqf`,
  `addons/nightvision/functions/fnc_applyNVGTubeModel.sqf`,
  `addons/lighting/config.cpp`.

## AEE engine reference, section: simulation, scheduler, physics, animation, ballistics, damage

Scope: the simulation step and scheduler, physics (PhysX), animation, the projectile
integrator, the damage/armour/anatomy model, and dynamic simulation. Every non-obvious
claim carries a source. Sources: acemod/arma3-wiki command DB v2.22 (`the parsed command database`;
"DB" below), BIKI pages fetched through Wayback ("BIKI" below), the derapified engine config
`the derapified core engine config (Dta/bin.pbo)` ("config.cpp"), and CBA_A3 source ("CBA" below).
Read-only for AEE. UK spelling throughout.

---

### 1. The scheduler and the simulation step

#### 1.1 Three execution contexts

- **Unscheduled (immediate)**. Code runs inside the calling instance. The caller waits.
  Contexts: `init.sqf`/config-init, `EachFrame` and `onEachFrame` event handlers, UI
  handlers, and `call` from unscheduled code. (BIKI "Scheduler" via Wayback, `sched.html`.)
- **Scheduled (cooperative)**. `spawn`, `execVM`, `exec`, `execFSM` add a script to the
  scheduler. Scripts run round-robin, longest-waiting-first, and a script that has not
  run for the longest is served first. Each frame the scheduler runs scripts for a
  **maximum of 3 ms** (50 ms during a loading screen). A script that reaches the budget
  is paused mid-execution and resumes in a later frame. (BIKI "Scheduler".)
- **Suspension**. `sleep`, `uiSleep`, `waitUntil`, `canSuspend`. Suspension is forbidden
  in an unscheduled context and raises "Suspending not allowed in this context". Test the
  context with `canSuspend`. (DB `canSuspend`; BIKI "Scheduler".)

Consequence: a `sleep 0.01` in scheduled code can wait far longer than 0.01 s, because
`sleep` only marks the script runnable and the engine checks the deadline on a later
frame. At 20 FPS the minimum interval is about 50 ms. (BIKI "Scheduler".)

#### 1.2 Timing commands and the AEE root cause

| Command | Meaning | Source |
|---|---|---|
| `diag_tickTime` | Real seconds since game start. Monotonic. | DB (since 0.50) |
| `diag_deltaTime` | **Duration of the previous frame** in seconds. | DB (since 1.96) |
| `diag_frameNo` | Frames displayed. | DB |
| `time` | Seconds since mission start, per client, stops on pause. | DB |
| `uiTime` | UI time. Advances during pause. `uiSleep` uses it. | DB `uiSleep` |
| `accTime` | Current simulation acceleration factor. | DB; BIKI `acc.html` |

`diag_deltaTime` is the **rendered frame** duration. It is not the wall-clock gap between
two calls of a slowed handler.

AEE measured (RPT) that the eye driver integrates with `diag_deltaTime` inside a 0.1 s
`CBA_fnc_addPerFrameHandler`, and under-integrates about 8x. The mechanism is now proved
from CBA source:

- `CBA_fnc_addPerFrameHandler` takes `[function, delay, args]`. The function receives
  `_this = [_args, _handle]`. **No per-call deltaTime is passed.** (CBA
  `addons/common/fnc_addPerFrameHandler.sqf`, raw fetch.)
- The executor advances a per-handler expected time by `_delay` and calls the function
  when `diag_tickTime` passes it. (CBA `addons/common/init_perFrameHandler.sqf`, snippet:
  `_x set [2, _delta + _delay]; [_args, _handle] call _function;`.)

So a 0.1 s handler runs about ten times a second. On each run, `diag_deltaTime` still
reports the last **frame** duration (about 1/FPS, for example 0.0125 s at 80 FPS). Ten
calls per second sum to about 0.125 s, not 1.0 s. That is about an 8x under-integration,
matching the measured 8x tau error.

**Correct integrator**: use wall-clock time. Compute `diag_tickTime - _lastTick` once per
handler call, or key the integration on `diag_tickTime`. CBA does not supply the delta, so
the caller must track its own.

`accTime` does not change `diag_deltaTime` semantics. `diag_deltaTime` remains the frame's
real duration. BIKI states `accTime`/`setAccTime` are distinct from `skipTime` (BIKI
`acc.html`). A game-time integrator must therefore scale real dt by `accTime` only if it
wants simulation time, and must not assume `diag_deltaTime` already carries the factor.

#### 1.3 skipTime and the missing world clock

No engine event fires on a time jump. `skipTime` and `setDate` move daytime and the sun
instantly. The command DB (2695 commands) holds no time-jump event handler. A driver that
samples scene luminance but keeps its own integrated clock cannot see the jump. It must
store a world clock (`dayTime` or `date`) each tick and detect the discontinuity.

`time` does not jump, because `skipTime` moves the date, not `time`. (Related section,
`sec-world.md`.) It is the wrong key for jump detection. AEE measured: at 19:02:59 the
scene read 68039 lx while adaptation held 4.37, aperture 24.4, so the scene stayed bright
for about 30 s.

**Rule for the fix**: the kernel gets `fnc_eyeTimeSkip`. The driver stores the previous
world clock and, when the jump exceeds the expected step, fast-forwards the adaptation
state. Do not use `diag_deltaTime` for the slow interval, and do not use `time` for the
jump.

---

### 2. Physics engine (PhysX) and simulation control

- `enableSimulation` / `enableSimulationGlobal` disable an entity's animation and
  **physics** simulation. The entity still takes damage and still reports enemies.
  `enableSimulation` acts locally; `enableSimulationGlobal` is global and JIP-safe and may
  run client-side with a local argument since A3. `simulationEnabled` reads the state.
  (DB.)
- `setVelocity` sets the velocity vector in m/s. Each component is clamped to +-5000 m/s
  since 2.06. It is a **local** command. It is affected by `setDir` and
  `setVectorDirAndUp`, so call it after those. (BIKI `setvel.html`; DB.)
- `setVelocityModelSpace`, `setVelocityTransformation`, `setMass`, `setCenterOfMass`,
  `setVehicleArmor`, `setDir`, `setVectorDirAndUp` shape the rigid body that PhysX
  integrates.
- `setObjectMaterial` selects the surface material (sound/particle response). It does not
  change the mass or the inertia tensor. UNKNOWN: whether it affects the contact model.

The PhysX solver, the contact solve, and the vehicle flight-dynamics model (FDM) are
engine-internal. There is no `setFlightModel`. (`engine-config-surface.md`;
AEE algorithm decision record ADR-017.) A mod sets the inputs and reads the results. It
cannot replace the integrator.

---

### 3. Animation system

#### 3.1 Object animation (config-driven)

- `animate [animationName, phase, speed]` activates a CfgModels animation. `phase` runs 0
  to 1. `speed` is a boolean (instant) since 0.50, or a Number (config-speed multiplier)
  since 1.66. The **config speed cannot be changed at runtime**. (BIKI `animate.html`.)
- `animateSource` is the recommended replacement. BIKI calls it "more efficient and
  optimised for multiplayer". Do not mix `animate` and `animateSource` on the same part.
  (BIKI `animate.html`.)
- `animateDoor`, `animationSourcePhase`, `animationPhase`, `animationNames` read or drive
  named model animations.

#### 3.2 Unit animation and multiplayer

- `switchMove` applies a move immediately and **resets** all animation states (aim,
  gesture). It is a **Local**-class command, but when executed locally on the unit it has a
  **global effect** and synchronises for JIP. On the executing machine the change is
  immediate. On remote machines it is transitional. For an immediate change on every PC,
  use global `remoteExec`. When the argument is remote, the change on the executing PC is
  only temporary. (BIKI `switchmove.html`.)
- `switchMove` fires no `AnimChanged` or `AnimDone` event. `playMove` does.
- `playMove` blends smoothly from the current state; `playMoveNow` forces the move;
  `switchAction`/`playAction` drive gestures; `setFaceAnimation` drives the face.
- `switchMove` reached alternative syntax in 2.18 (`[moveName, time, blendFactor,
  resetAim]`). Use it instead of the `switchMove` + `playMoveNow` pair. (BIKI
  `switchmove.html`.)

**MP rule**: pump animation commands through `remoteExec` when the change must appear
immediately on every client. A server-side `switchMove` without `remoteExec` arrives
transitional and can be overwritten by the engine's own state sync. Motion is asset-gated:
a new animation needs a shipped `.rtm` motion file. A mod cannot synthesise motion from
config alone. (`engine-config-surface.md`.)

---

### 4. Ballistics and the projectile integrator

CfgAmmo and CfgMagazines carry the ballistics inputs. From the engine config
(`the derapified core engine config (Dta/bin.pbo)`):

- `CfgAmmo >> Default` (line 2429): `hit`, `indirectHit`, `indirectHitRange`,
  `underwaterHitRangeCoef`, `typicalSpeed = 900`, `explosionForceCoef`, `maxSpeed`,
  `simulationStep = 0.05`, `tracerColor`, `timeToLive = 10` (sample).
- `airFriction = -0.0005` (line 2557, sample). 21 `airFriction` entries in the base
  config.
- `caliber`, `deflecting`, `thrust`, `thrustTime` (lines 2501-2603).
- `CfgMagazines >> Default` (line 2916): `initSpeed = 100`, `maxLeadSpeed = 50`, `count`,
  `ammo`.

These are **inputs**. The projectile integrator itself is engine-internal and is not
script-replaceable. A mod changes the trajectory by changing the inputs. It can also read
the flight: CBA tracks projectiles with a 0.1 s PFH (CBA
`addons/diagnostic/fnc_projectileTracking_handleFired.sqf`). (`engine-config-surface.md`;
ADR-017.)

One exception, community-proved: **ACE3 advanced ballistics reimplements the flight in
script** and hides the engine projectile. A mod can, in principle, replace the trajectory
by spawning and integrating its own projectile. This is a full reimplementation, not a
config change. (`github.com/acemod/ACE3`, advanced ballistics module.)

Firing commands: `fire` forces a weapon; it can take a remote unit but this is unreliable,
and `selectWeapon` is local only, so run `fire` where the unit is local. `doFire` orders
fire on a target without radio. `commandFire` orders fire by radio. `magazinesAmmo` reads
magazine counts. (DB; BIKI `fire`.)

Artillery: `doArtilleryFire`, `commandArtilleryFire`, `getArtilleryETA`,
`inRangeOfArtillery`. (DB.)

---

### 5. Damage, armour and anatomy

- `setHitPointDamage [hitPointName, damage, useEffects, killer, instigator]`. `damage`
  runs 0 to 1 by named config class. `useEffects` (since 1.68) skips destruction effects.
  `killer` (2.08) and `instigator` (2.12) feed the kill statistics and the `Killed`
  handler; `killer` and `instigator` are **server** arguments. The command is **Local**.
  It has no effect while `allowDamage` is false. (BIKI `shpd.html`.)
- `getHitPointDamage`, `setVehicleArmor`.
- `allowDamage` does not block scripted damage from `setDamage`, `setHit`,
  `setHitIndex`, or `setHitPointDamage`. (DB `allowDamage`.)

The anatomy model (hit points, armour, body-part damage flow) is engine-internal. Firing
and explosion damage route through the `HandleDamage` event and then into the hit-point
tree. `setHitPointDamage` writes the result directly. The exact body-part coefficient flow
is not exposed. **UNKNOWN**: the precise per-part damage-flow coefficients.

---

### 6. Dynamic simulation (A3 1.68+)

- `enableDynamicSimulationSystem` toggles the whole system. `enableDynamicSimulation`
  flags an object or group. `setDynamicSimulationDistance` sets a category activation
  distance; `setDynamicSimulationDistanceCoef` sets the multiplier. Getters exist for
  each. (DB, all since 1.68.)
- The system works on **groups**. A group that contains a player cannot be dynamically
  simulated. The command has no effect on mines. (DB.)
- Defaults: infantry 500 m, crewed vehicles 350 m, empty vehicles 250 m, props nearer.
  Moving entities get a 2x multiplier. Activation distance is limited by the player's
  object view distance by default. (BIKI `dyn.html`.)
- Group setting overrides per-entity setting. (BIKI `dyn.html`.)
- Waking: player units wake anything. Non-player units wake only **enemy** units. The
  engine uses a multi-grid proximity check, with a measurement error equal to the smallest
  cell. (BIKI `dyn.html`.)
- Limitations: no line-of-sight detection, so a disabled unit can be seen frozen with no
  ambient animation. Dynamic simulation overwrites the Eden "Enable Simulation" attribute.
  (BIKI `dyn.html`.)

**AEE note**: dynamic simulation can disable the eye driver's subject if the driver runs on
the entity's simulation. Keep the eye adaptation on the player (never dynamically
simulated) or on a client-side PFH, not on the simulated entity.

---

### 7. Ceilings: what a mod cannot change

1. **Scheduler budget and order**: 3 ms per frame, longest-waiting-first, engine-fixed.
   (BIKI "Scheduler".)
2. **`diag_deltaTime` semantics**: it is the frame duration, always. It cannot be made to
   report a handler's interval. (DB.)
3. **PhysX solver and vehicle FDM**: engine-internal. No `setFlightModel`.
   (`engine-config-surface.md`; ADR-017.)
4. **Projectile integrator**: engine-internal. A mod changes inputs (CfgAmmo/CfgMagazines)
   or replaces the flight in script (ACE3). (`engine-config-surface.md`.)
5. **Animation motions**: asset-gated by `.rtm`. Config alone cannot create motion.
   (`engine-config-surface.md`.)
6. **Dynamic-simulation activation logic**: engine grid. No line-of-sight input.
   (BIKI `dyn.html`.)
7. **Damage anatomy coefficients**: engine-internal. UNKNOWN.
8. **No time-jump event**: the engine fires no handler on `skipTime`/`setDate`. The driver
   must poll a world clock. (DB has no such command.)

---

### 8. In-scope command limits (quick table)

| Command | Locality / MP | Limit |
|---|---|---|
| `spawn` / `execVM` | scheduled | starts next frame; budget 3 ms/frame |
| `call` | inherits context | blocks the caller; suspension forbidden if unscheduled |
| `diag_deltaTime` | read | last frame duration, not handler interval |
| `diag_tickTime` | read | monotonic wall clock; use for dt |
| `accTime` | read | factor; does not alter `diag_deltaTime` |
| `enableSimulation` | local | stops anim + physics; damage still applies |
| `enableSimulationGlobal` | global/JIP | same effect; client-side allowed |
| `setVelocity` | local | +-5000 m/s per component; apply after `setDir` |
| `animate` / `animateSource` | global effect | config speed fixed at runtime |
| `switchMove` / `playMove` | local, engine-syncs | remoteExec for immediate everywhere |
| `setHitPointDamage` | local | no effect if `allowDamage` false; killer/instigator server |
| `fire` | run where local | remote unit unreliable; `selectWeapon` local |
| `enableDynamicSimulation` | group-level | no player groups; no mines |

---

### Sources

- Command DB: acemod/arma3-wiki dist v2.22, `the acemod command database`,
  parsed `the parsed command database`.
- BIKI via Wayback (2024): Scheduler, `animate`, `switchMove`, `setVelocity`,
  `setHitPointDamage`, `accTime`, "Dynamic Simulation". Local copies in
  `the Wayback page mirror`.
- Engine config: `the derapified core engine config (Dta/bin.pbo)` (CfgAmmo 2429, CfgMagazines 2916,
  CfgMovesBasic 8302).
- CBA_A3 source: `github.com/CBATeam/CBA_A3` `addons/common/fnc_addPerFrameHandler.sqf`,
  `addons/common/init_perFrameHandler.sqf` (GPL-2.0).
- ACE3 advanced ballistics: `github.com/acemod/ACE3`.
- AEE ceilings: `engine-config-surface.md`; ADR-017.

## Arma 3 Engine Reference — Config, Network+JIP, Mission Model, Files+IO, Diagnostics

Reference for AEE. Compiled 2026-10-08. British English, STE. Every non-obvious claim carries a source. "BIKI says" means a
Community Wiki page. "DB" means the structured command DB
`the acemod database entry <name>.yml` (acemod/arma3-wiki dist v2.22).

### 0. Evidence base

- Command DB: `the acemod database commands/*.yml` (2695 commands). Parsed:
  `the parsed command database`, `the grouped command list`.
- BIKI pages fetched through the Wayback workaround into
  `the local BIKI page mirror`: `publicVariable`, `remoteExec`,
  `Arma_3:_Remote_Execution`, `Arma_3:_CfgRemoteExec`, `Multiplayer_Scripting`
  (via `Join_In_Progress`), `Description.ext`, `CfgFunctions` (Functions Library),
  `Initialisation_Order`, `Event_Scripts`, `Config.cpp/bin File Format`,
  `Arma_3:_Startup_Parameters`.
- Engine config ground truth: `engine-config-surface.md` (config roots
  and merge rules) and `the unpacked functions_f scripts` (engine scripts).
- Engine scripts: `functions_f/initFunctions.sqf`, `functions_f/Scripts/initPlayerServer.sqf`.

### 1. The network model and locality

The engine is client–server. The server distributes state. It is either a dedicated
machine or hosted by a player (BIKI `Multiplayer_Scripting`). `isServer` is true on a
dedicated server, on a player-hosted server, and in single player. `isDedicated` is
true only on a dedicated server. `hasInterface` is true when a human player is present
(false for a dedicated server and a headless client). `isMultiplayer` is true in any
network game.

Machine and object network IDs (BIKI `Multiplayer_Scripting`):

- The server always has network ID 2. The first client is 3, the next is 4. The
  current machine reads its ID with `clientOwner` (DB).
- `owner object` gives the machine ID of an object's owner. `groupOwner group` gives
  the group owner. `netId` gives an object's network ID. `objectFromNetId`,
  `groupFromNetId` reverse it.
- Target value 0 means everyone (server included). Target value 1 is reserved and
  not implemented. A negative value excludes that machine ID. Two negative owners in
  one target array do not work: `args remoteExec ["func", [-2, -3]]` executes on
  every client (BIKI `remoteExec`, note by Sa-Matra, 2024-09-19).

Locality is an attribute of the machine where the code runs (BIKI
`Multiplayer_Scripting`). A player's unit is always local to that player's machine. A
dedicated server has no player (`isNull player` is true). An AI group with a player
leader is local to that player's machine. A driven vehicle is local to the driver's
machine, not the commander's or gunner's. Terrain objects are local everywhere.
Editor-placed objects and empty vehicles are local to the server. Editor-placed
triggers run on every machine unless the Eden "Server Only" option is set. `createUnit`
and `createVehicle` make objects local to the machine that issued the command.

Locality changes on a leader death (AI transfers to the new leader's machine), on a
joining AI unit, when a player enters an empty vehicle, and on team switch or
`selectPlayer`. Since Arma 3 the "Local" event handler fires on a locality change
(BIKI `Multiplayer_Scripting`, `addEventHandler` supports it).

The locality markers matter. `LA` = local argument, `GA` = global argument, `LE` =
local effect, `GE` = global effect, `SE` = server execution (BIKI). Example: `setFace`
has global argument and local effect, so it does not propagate; a designer who wants
the new face everywhere must use `[unit, "Miller"] remoteExec ["setFace", 0]`.

### 2. publicVariable and JIP

`publicVariable "varName"` broadcasts a `missionNamespace` variable and its current
value to all machines (DB, BIKI `publicVariable`). It is not automatic: a later change
needs another broadcast. It works only for a declared global variable, and the name
must be a quoted string — `publicVariable TAG_BossName` tries to broadcast the value
and fails (BIKI example 3).

Supported types (DB): Number, Boolean, Object, Group, String, Text, Array, Code,
nil (since 2.02), HashMap (since 2.26). It cannot transfer a local reference:
scripts, displays, and local (`createVehicleLocal`) objects are impossible. Team
Member is unsupported.

JIP behaviour (DB, BIKI): a variable broadcast with `publicVariable` during a mission
is sent to a JIP client with the value at broadcast time, before the first batch of
client-side event scripts (such as `init.sqf`) runs. The variable is persistent.

`publicVariableServer "v"` sends a client value to the server. `publicVariableClient`
is `clientID publicVariableClient "v"`, where the client ID is `owner player`. Both
carry the same type limits (DB).

The important JIP ceiling: a JIP client synchronises `publicVariable`-sent variables,
but it does NOT re-synchronise variables it received with `publicVariableClient`
after a disconnect/reconnect. Only server-known `publicVariable` variables sync
(BIKI `Multiplayer_Scripting`, "How it works").

The `setVariable` alternative syntax broadcasts without a separate command:
`obj setVariable [name, value, public]` with `public` true spreads the value over the
network and is JIP-synchronised (DB; BIKI JIP table). The engine supports broadcasting
nil to delete the variable (since Arma 3). Two limits: a nil-assign does not remove
the name from `allVariables` for an Object or scripted Location (DB); and variables in
`missionNamespace`, `uiNamespace`, `parsingNamespace` and `profileNamespace` must not
be named as commands (for example `west`), or the engine raises "Reserved variable in
expression" (DB).

BIKI warns that frequent `publicVariable` calls, or large payloads, cause bandwidth
problems. It states no byte figure. An exact transport size limit is UNKNOWN — no
source in the kit gives a number. Treat "keep it small and infrequent" as the only
documented rule.

### 3. remoteExec

`remoteExec` and `remoteExecCall` (since 1.50) run a function or command on target
machines (DB, BIKI `Arma_3:_Remote_Execution`). `remoteExec` runs functions in the
scheduled environment (suspension allowed). `remoteExecCall` runs them unscheduled.
Script commands always run unscheduled under either form. The "Call" does not mean
"runs immediately" — it means "unscheduled".

Syntax: `params remoteExec ["order", targets, JIP]`. `targets` defaults to 0
(everyone). `JIP` defaults to false. When JIP is used the command returns the JIP ID;
an Object, Group or netId target returns the netId.

`BIS_fnc_MP` is deprecated. It was rewritten in 1.54 to call `remoteExec`/`remoteExecCall`
internally, for backward compatibility, but it "should no longer be used" (BIKI). The
engine still holds a harmless stub: `functions_f/initFunctions.sqf` line 22 sets
`BIS_fnc_MP_packet` and comments it "is not used anymore".

Security and filtering, `CfgRemoteExec` (BIKI `Arma_3:_CfgRemoteExec`). The rules
apply to clients only. The server is not limited. The more local config wins:
mission `description.ext` > campaign `description.ext` > game/mod config. If several
`CfgRemoteExec` blocks exist, the last parsed sets `mode` and the whitelists merge.
Values: `mode` 0 = blocked, 1 = whitelist only, 2 = fully allowed (default). `jip`
0/1 controls the JIP flag. Per element: `allowedTargets` 0 = all, 1 = clients only,
2 = server only; `jip` overrides the parent. A mission should use `import` to keep a
mod's entries. `remoteExec` is also filtered by BattlEye's `remoteexec.txt` (BIKI:
the filter string is `format ["%1 %2", functionName, str params]`).

Validity is checked twice: at issue on the client, and before the server broadcasts.
If the function does not exist, the parameters are malformed, CfgRemoteExec blocks
it, or JIP is disallowed, the request is dropped (BIKI `Arma_3:_Remote_Execution`).

JIP queue (BIKI `Arma_3:_Remote_Execution`, DB `remoteExec`):

- A persistent call (JIP true, or a custom ID) is stored on the server under a unique
  JIP ID. A JIP player runs all queued entries.
- Reusing the same JIP ID overwrites the earlier message. `remoteExec ["", "JIPid"]`
  removes it.
- Order of persistent remote execution for JIP players is NOT guaranteed. Non-JIP
  remote execution is queued and runs in order (DB multiplayer note; BIKI example 8).
- A JIP + server-only target fails: `[args] remoteExec ["cmd", 2, true]` does not work
  (BIKI `remoteExec`, note by Pierre MGI, 2017-01-30).

Introspection: `isRemoteExecuted` is true in a remote-executed context (always false
in single player). `isRemoteExecutedJIP` is true only for a JIP-queued call.
`remoteExecutedOwner` gives the initiating machine ID; it returns 0 in single player,
outside remote execution, or from a headless client (DB).

Avoid `[code] remoteExec ["call"]` or `["spawn"]`: CfgRemoteExec can block `call` and
`spawn`, and remote commands run unscheduled (BIKI warning). Use a named function.

### 4. Config and class system

Roots: `configFile` is the game/mod config root. `missionConfigFile` is the mission
`description.ext` root. A campaign has `campaignConfigFile`. The more local config
wins (BIKI `Arma_3:_CfgRemoteExec` states the order: mission > campaign > game).

Config file format (BIKI `Config.cpp/bin File Format`): `config.cpp` is text and
`config.bin` is binarised. Both may sit in one PBO, but the `.bin` is ignored
whenever the `.cpp` is present. A `.cpp` is required for `#include`, `__EVAL` and
`__EXEC`. A folder in a PBO that holds a config and `CfgPatches` is its own addon;
mission PBOs hold no config (mission addons do).

The override rules are mapped in `engine-config-surface.md`. In brief:

- A bare reopen `class X {}` strips the parent and logs `Updating base class '<p>'->''`.
  X loses `scope`, `size`, `drawStyle` and every other inherited key. This caused AEE's
  `No entry CfgMarkers/*.scope` and `Wrong location draw style` in the RPT.
- The parent restatement rule: reopen a vanilla class as `class X: <realParent>`. Never
  add a parent to a parentless vanilla class (that logs `Updating base class ''->'<name>'`).
- Forward-declare an external parent at the correct nested scope only. A file-root
  `class Y;` creates an empty class and re-parents the real one. HETT reports `L-C03`
  and `L-C04`.
- Class names are case-insensitive (`Church` equals `church`). The merge is
  last-loaded-wins per property. `requiredAddons[]` sets load order.

Config commands (DB): `configClasses` returns subclasses that pass a condition and
does not see inherited properties. `configProperties` is slower but sees inherited
properties. `inheritsFrom` gives the base entry. `isClass`, `isKindOf`, `configName`,
`getNumber`, `getText`, `getArray` read the entry. `getMissionConfigValue` and
`getMissionConfig` are Eden-aware: they check `description.ext` first, then the Eden
scenario attribute (DB).

`diag_exportConfig [path, config]` writes any config to a file (DB, since 2.2) — use
it to prove the merged config at run time.

Namespaces (DB): `missionNamespace`, `uiNamespace`, `profileNamespace` (the user
profile; saved on game close or by `saveProfileNamespace`), `parsingNamespace` (the
config parser). `localNamespace` (since 2.0) has the same lifetime as the mission
namespace, but variables cannot be broadcast in or out and are not serialised on save.

### 5. Mission model

`description.ext` is the `missionConfigFile`. It uses config syntax and supports a
limited class set (BIKI `Description.ext`). The `class` keyword must be lowercase. The
notable classes: `CfgFunctions`, `CfgRemoteExec`, `CfgTasks`, `CfgTaskTypes`,
`CfgTaskDescriptions`, `CfgDebriefing`, `CfgDebriefingSections`, `CfgRespawnTemplates`,
`CfgRespawnInventory`, `CfgSounds`, `CfgMusic`, `CfgRadio`, `CfgSFX`, `CfgSentences`,
`CfgNotifications`, `CfgHints`, `CfgLeaflets`, `CfgUnitInsignia`, `CfgIdentities`,
`CfgVehicleTemplates`, `CfgUnitTemplates`, `CfgCameraEffects`,
`CfgPostprocessTemplates`, `CfgLoadingTexts`, `CfgDisabledCommands`, `CfgCommands`,
`CfgCommunicationMenu`, `CfgRoles`. Since 2.02 `import` allows inheritance from the
main config. `briefingName`, `onLoadName` and `overviewText` in `description.ext`
override the Eden values.

Mission identity: `missionName` returns the workshop user-friendly name; `missionNameSource`
reads `mission.sqm` (pre-2.02 may be empty). `worldName` returns the loaded world. The
mission itself is `mission.sqm`; the mission PBO holds no config (see §4).

`CfgFunctions` (BIKI Functions Library) has three levels: tag, category, function. A
function is named `<tag>_fnc_<name>`. `file` on the category is required for a mod and
sets the load path. `requiredAddons` on the category skips the category if an addon is
missing. Per function: `preInit` (before object init, unscheduled), `postInit` (after
object init, scheduled, receives `["postInit", didJIP]`), `ext` (`.sqf`/`.fsm`), and
`recompile`. Functions are compiled with `compileFinal` (anti-hack).

Event scripts (BIKI `Event_Scripts`): `init.sqf`/`init.sqs` at mission start;
`initServer.sqf` on the server only; `initPlayerLocal.sqf` on each player join (start
and JIP, params `["_player", "_didJIP"]`); `initPlayerServer.sqf` on the server per
player join (needs `BIS_fnc_execVM` as a whitelisted remote call, so BIKI recommends
avoiding it); `initJIPcompatible.sqf`; `exit.sqf`; `onPlayerKilled/Respawn.sqf`.

Initialisation order (BIKI `Initialisation_Order`): recompile functions → preInit
functions → object init event handlers → object init fields → (SP) init.sqs/sqf →
scenario attribute expressions → persistent functions → modules → `initServer.sqf`
(server) → `initPlayerLocal.sqf` (client) → `initPlayerServer.sqf` (client/server) →
postInit functions → (MP) init.sqf. All init fields run again for every JIP player,
so global-effect code such as `setDamage` re-executes on JIP (BIKI JIP warning).

JIP and the mission (BIKI `Multiplayer_Scripting`): `didJIP` is true for a JIP client.
`didJIPOwner object` is true on the server when an object's owner joined JIP.
`getClientState`/`getClientStateNumber` give the connection state. A server can never
be JIP. JIP stays available while respawn is enabled, even if the designer disables
AI slots (BIKI). `disabledAI = 1` fills slots with players only.

### 6. Files and IO

- `loadFile path` returns raw file content (DB). It does not strip comments, so
  `compile loadFile "f.sqf"` throws an error if the file has comments. Use
  `preprocessFile` instead. Non-UTF-8 bytes above 127 can convert wrongly.
- `preprocessFile path` returns content after the C-like preprocessor (comments,
  `#define` etc.). No caching, so do not call it in a time-critical loop; UTF-8 only
  (DB).
- `preprocessFileLineNumbers path` is the same but prepends `#line 1 "file"` for the
  compiler (DB).
- `compile string` turns a string into Code; `call compile` runs it. The DB notes a
  file intended for `compile` must be comment-free. `call compile` cannot be
  whitelisted safely (BIKI `CfgRemoteExec` warns about `BIS_fnc_execVM`).
- `saveProfileNamespace` writes the profile to disk. It triggers a slow file
  operation, so do not call it often, and do not store large data (DB warning). The
  profile saves on close anyway.

### 7. Diagnostics and the RPT

The report file (RPT) is the engine log. `diag_log value` writes one line to it (DB).
The diagnostic family (DB `raw-commands.md` §1455-1486):

- `diag_tickTime` — real seconds since game start (Windows `timeGetTime`).
- `diag_deltaTime` — duration of the previous frame in seconds (since 1.96). This is a
  frame duration, not a wall-clock delta. A per-frame handler that integrates with it
  under-counts when it runs less often than the frame rate.
- `diag_activeScripts` — 4-element array: spawn, execVM, exec, execFSM counts.
- `diag_captureFrame n` — capture frame n; on a server it writes to file instead of UI.
  `diag_captureFrameToFile n` writes beside the RPT.
- `diag_captureSlowFrame [section, threshold, frameSkip, toFile, continuousCounter]` —
  capture a frame that exceeds a threshold; `toFile` since 2.20.
- `diag_codePerformance [code, args, cycles, ignoreTimeLimit]` — unscheduled benchmark;
  in multiplayer it runs one cycle only unless the debug console is enabled (DB).
- `diag_exportConfig [path, config]` — write a config to disk (since 2.2).
- `diag_dumpCalltraceToLog`, `diag_dumpScriptAssembly`, `diag_SQFCDebugDump` — dump
  the current callstack or bytecode.
- `exportJIPMessages "name"` — write the JIP queue to a file beside the RPT (since 1.56).

`enableDebugConsole` is a `description.ext` key (BIKI `Description.ext`): value 1, 2
(2 is dangerous in multiplayer), or an array of Steam UIDs `{ "7656...", }` for
specific users. The `dump` command is not in the DB — mark UNKNOWN. `getDLCs filter`
returns the app IDs of owned DLCs (DB).

### 8. Ceilings (summary)

| Area | Ceiling | Evidence |
|---|---|---|
| publicVariable | No documented byte limit; frequency and payload cause bandwidth loss. Local refs, scripts, displays, `createVehicleLocal` objects and Team Member cannot be sent. | DB `publicVariable`; BIKI note. Exact size = UNKNOWN |
| JIP | `publicVariableClient` values do not re-sync on reconnect; JIP persistent order not guaranteed; all init fields re-run per JIP player; no server JIP. | BIKI `Multiplayer_Scripting`, `Arma_3:_Remote_Execution` |
| remoteExec | Client-side only filtered by `CfgRemoteExec` (server exempt); JIP + server-only target fails; two negative owners do not work; `call`/`spawn` may be blocked; BattlEye `remoteexec.txt`. | BIKI `CfgRemoteExec`, `remoteExec` |
| Config merge | Last-loaded-wins per property; a bare reopen strips the parent; class names case-insensitive; a file-root forward declaration destroys the parent; engine core is unreachable. | `engine-config-surface.md` |
| setVariable | nil-assign does not delist the name for Object/Location; mission/ui/parsing/profile namespace variables must not be named as commands. | DB `setVariable`, `allVariables` |

### 9. Sources

- DB: `the acemod database entries for {publicVariable,remoteExec,setVariable,getVariable,configFile,missionConfigFile,diag_log,...}`
  and `the parsed command database`.
- BIKI (Wayback 2024):
  https://web.archive.org/web/2024/https://community.bistudio.com/wiki/Multiplayer_Scripting ,
  `/publicVariable`, `/remoteExec`, `/Arma_3:_Remote_Execution`, `/Arma_3:_CfgRemoteExec`,
  `/Description.ext`, `/Arma_3:_Functions_Library`, `/Initialisation_Order`,
  `/Event_Scripts`, `/Config.cpp/bin_File_Format`.
- Engine scripts: `the shipped functions_f initFunctions.sqf`,
  `functions_f/Scripts/initPlayerServer.sqf`.
- Config surface: `engine-config-surface.md`.

## Engine reference — World: time, weather, terrain, map, sound

Research for AEE. No AEE file was changed for it.
Sources: command DB `the acemod database entry <name>.yml` (acemod/arma3-wiki
dist v2.22, a structured BIKI mirror); shipped engine configs
`the derapified core engine config (Dta/bin.pbo)` (Dta/bin.pbo) and
`the derapified map_altis.pbo config` (map_altis); ground-truth scripts
`the unpacked functions_f scripts` and `.../sounds_f/config.cpp`.
Labels: **config proves** = shipped config field; **command DB** = the YML mirror
of BIKI; **BIKI (Wayback)** = fetched page; **engine source proves** = open
Bohemia engine (CWR). Non-obvious claims cite the file or URL.

---

### 1. Time commands

`time` returns seconds since mission start; it is local and stops when the game
pauses. Unlike `uiTime` it does not use real time. Use `serverTime` for one
unified clock (command DB `time`). `daytime` is the hour 0..24. `date` is
`[year,month,day,hour,minute]`, local in MP.

- `skipTime <hours>` — jumps the time of day and the tides; no units move; lower
  cloud layers jump at once. Since 2.10 it is capped at ±1000 hours per skip
  (game stability). Server `skipTime` syncs in about 5 s and is JIP-safe; a
  client `skipTime` reverts to server time in about 5 s. For large jumps use
  `setDate` (command DB `skipTime`, important note).
- `setDate [y,m,d,h,min]` — local. Clients resync to the server date
  periodically; to change all at once use `remoteExec ["setDate"]`. Out-of-range
  values roll over ("hour 25" becomes next day 01:00). Leap-year defect: the
  engine creates 29 February but removes 31 December, so `setDate
  [1980,12,31,12,0]` jumps to `[1981,1,1,12,0]` (command DB `setDate`).
- `setTimeMultiplier v` — cap **0.1 to 120**; global effect (command DB).
- `setAccTime f` — simulation acceleration. Disabled in multiplayer. NOT
  clamped: negative or large values give undefined behaviour (command DB,
  `problem_notes`).

**AEE relevance.** No time command emits a jump event. The engine changes
`daytime` and the sun position instantly on `skipTime`/`setDate`, but there is
no `timeSkip` event handler in the command DB. A driver that samples scene
luminance but keeps its own integrated clock cannot see the jump. The fix must
store a world clock (`daytime`/`date`) and detect the discontinuity. `time`
itself does NOT jump (`skipTime` moves the date, not `time`), so `time` is the
wrong key.

### 2. Weather and atmosphere model

Relations (command DB, corroborated by the world config):

- `overcast` 0..1 maps clear to full cloud. Higher overcast raises wind.
- `rain` 0..1. Rain is not possible below overcast 0.7 (BIKI) / 0.5 in A3
  (command DB `setRain`).
- `fog` 0..1 getter; `setFog [time, fog]` or `setFog [time, [value, decay,
  base]]`. A negative decay gives a "ceiling" fog (command DB).
- `wind` is the horizontal vector in m/s; `windDir` is the azimuth the wind
  comes FROM; `windStr` 0..1. Setters: `setWindStr`, `setWindDir`,
  `setWindForce` (max wind change rate).
- Read-only state: `gusts`, `waves`, `rainbow`, `humidity`, `temperature`
  (2.8), `pressure`.

**Locality.** `setOvercast`, `setRain`, `setFog`, `setWindDir` on the SERVER
propagate globally; on a CLIENT the effect is local and temporary and reverts to
the server value. Since 2.10 the weather values are periodically synced with the
server (command DB, multiplayer notes). `forceWeatherChange` applies pending
settings at once, skipping smooth transitions; it can cause lag. To stop the
engine overwriting custom weather, enable *Manual Control* in the Eden intel
section (command DB `forceWeatherChange`). `nextWeatherChange` is the seconds
left in the current transition; after it the engine creates a new random change
over at least 90 minutes (command DB).

**Forecast.** `overcastForecast`, `fogForecast` return the local forecast.
`fogParams` returns the extended fog array. The automatic system moves *toward*
the config `forecast*` fields.

**Weather config (config proves).** `CfgWorlds/DefaultWorld` (`bin/config.cpp`
:16499-16520) and Altis (`map_altis_extract/config.cpp:463-472`) carry:
`startWeather`, `startFog`, `startFogBase`, `startFogDecay`, `forecastWeather`,
`forecastFog`, `forecastFogBase`, `forecastFogDecay`, `fogBeta0Min/Max`,
`hazeBaseHeight`, `hazeBaseBeta0`, `hazeDensityDecay`, `startWind`,
`startWindDir`, `startWaves`, `startRain`, `startLightnings`, `startGusts`,
`forecastWind`, `forecastWaves`, `forecastRain`, `forecastLightnings`,
`forecastGusts`, `forecastWindDir`. Nested `RainConfig` has
`minRainDensity`/`maxRainDensity`; `WindConfig` has `minGustCount`/`maxGustCount`,
`minGustValue`/`maxGustValue`, `speedOfWindChange`, and `windSpeedCoef = 10.0`;
`LightningsConfig` and `RainbowConfig` are present. `setWaves` has no effect
unless *Manual Override* is selected (command DB `setWaves`).

**AEE relevance.** The engine changes sun and overcast instantly on `skipTime`.
Fog, rain and overcast otherwise transition smoothly over the given time. There
is no event for a weather jump. The scene-luminance probe in the RPT
(19:02:59, scene = 68039 lx but adapted = 4.37, aperture 24.4) shows the eye
driver lagging an instant engine change.

### 3. Terrain, WRP and the cell model

`getTerrainInfo` (2.10) returns
`[landGridWidth, landGridSize, terrainGridWidth, terrainGridSize, seaLevel]`
(BIKI Wayback `getTerrainInfo`):
- `landGridWidth*landGridSize` and `terrainGridWidth*terrainGridSize` both equal
  `worldSize` exactly.
- **land grid** drives object placement, `nearestObject` and dynamic simulation.
- **terrain grid** IS the terrain: it displays the terrain, and gives terrain
  height and surface normal. `terrainGridWidth` is the cell size;
  `terrainGridSize` is the heightmap resolution.
- Altis: `[30,1024,7.5,4096,0]`. Cell size **7.5 m**, 4096 heightmap pixels,
  worldSize 30720 m. Stratis: `[32,256,4,2048,0]`. `seaLevel` is 0 when tides
  are off.

`getTerrainHeight pos` returns the height at the **closest terrain grid pixel**
(it rounds to the cell), unlike `getTerrainHeightASL` which samples the exact
position (command DB). On Altis that quantises to 7.5 m cells.

`setTerrainHeight [[x,y,asl],...], adjustObjects` (server-side, global effect):
changes are **internally rounded to heightmap coordinates**; stored in the JIP
queue; not removed when a value is reset; sections can become invisible on
extreme change; walking an edge can catapult the player; and edits are NOT saved
in savegames (command DB, important block). Every object above the change is
adjusted, including flying objects. To keep the JIP queue clean, edit whole
terrain *sections* and repeat every position each update.

`worldSize` is the terrain side length in metres (command DB). `worldName`
returns the world path string; config proves Altis `worldName =
"\A3\map_Altis\Altis.wrp"` and `mapSize = 30720`
(`map_altis_extract/config.cpp:2284,2291`). `BIS_fnc_mapSize` only reads the
`mapSize` config number (`functions_f/Map/fn_mapSize.sqf`). `surfaceType` and
`surfaceTexture` return the ground surface, even under buildings and roads.

**WRP ground truth.** `Altis.wrp` starts with the ASCII magic `OPRW` (little
endian "WRP") — `the Altis world file (Altis.wrp)`, 183 MB. The WRP
holds the heightmap and the object placement. The cell model above is the
heightmap grid.

**Ceiling.** The terrain cell size and heightmap resolution are baked in the WRP
and cannot be changed at runtime. `setTerrainHeight` is the only terrain
mutation, and it is cell-aligned and lossy.

### 4. Map and markers

`createMarker ["name", pos]` creates the marker on every connected and JIP
player; the name must be unique or the call is ignored. The marker is invisible
until `setMarkerType` defines a `CfgMarkers` class (command DB `createMarker`).
`getMarkerPos` returns 3D when the z-coordinate was stored; that z is used by
`createVehicle`/`createUnit`/`createAgent`/`setVehiclePosition`. `allMapMarkers`
includes user markers named `_USER_DEFINED #<PlayerID>/<MarkerID>/<ChannelID>`.

Marker setters: `setMarkerPos`, `setMarkerType`, `setMarkerColor`,
`setMarkerSize`, `setMarkerDir`, `setMarkerShape`, `setMarkerText`,
`setMarkerBrush` (a `CfgMarkerBrushes` class), `setMarkerAlpha`,
`setMarkerPolyline`. A non-existent shape defaults to `RECTANGLE`. A polyline
path must have `count >= 4` and an even count (command DB).

**MP cost (command DB).** Every global marker command broadcasts the *entire*
marker state. Do all but the last edit with the *Local* commands, then issue one
global command. `setMarkerDrawPriority` (2.14) is LOCAL despite its name; higher
priority draws on top; before 2.18 `createMarker` forced a new marker to the end
of `allMapMarkers`, giving it top priority.

Map control: `drawIcon`, `drawLine`, `drawArrow` draw on a `CT_MAP` and must be
called from the `onDraw` UI event handler; `drawLine` can reduce frame rate
(command DB). `ctrlMapScreenToWorld`/`ctrlMapWorldToScreen`,
`ctrlMapAnimAdd`/`ctrlMapAnimCommit` animate. `ctrlMapScale` gives the zoom.

**Grid (config proves + engine source).** Grid geometry is read from
`CfgWorlds >> <worldName> >> Grid`. `DefaultWorld/Grid` (`bin/config.cpp:16403`)
and Altis Grid (`map_altis_extract/config.cpp:2326`) declare `Zoom1..ZoomN` with
`zoomMax`, `format`, `stepX`, `stepY`, and `offsetX/offsetY`. Altis uses
`zoomMax` 0.05 / 0.5 / huge, `stepX` 100 / 1000 / 10000, and `offsetY = 30720`
with negative `stepY` (grid origin at the north edge). `BIS_fnc_mapGridSize`
reads `zoomMax` and `stepX` from these classes to return the current grid square
size (`functions_f/Map/fn_mapGridSize.sqf`). Prior research
(`arma-map-grid-semantics.md`) maps `colorGrid` to the edge
coordinate numbers and `colorGridMap` to the in-map lines, from open engine
source `BohemiaInteractive/CWR UIMap.cpp`. So `alpha(colorGrid) = 0` hides the
edge numbers.

**Ceilings (prior research, ADR-029/030).** Contour geometry and interval are
engine-derived; only the colour and the `showCountourInterval` label are
settable. The satellite raster is baked per world (`pictureMap` +
`mapDrawingBrightnessModifier`, Altis 1.5). Object-to-icon routing is
engine-internal (ceiling **T157884**); marker texture aspect stretches
(**T170754**). See `topo-map-surface.md`.

### 5. Sound engine

Two families.

**Non-positional / UI.** `playSound "cfgName"` plays a `CfgSounds` class, local
effect, optional `[isSpeech, offset]`, returns the speaker object since 2.0.
`playMusic "cfgName"` plays a `CfgMusic` class, local; `playMusic ""` stops it.
`fadeSound [time, volume]` fades locally; **Final Volume = Client Setting ×
Scripted Volume**, so a script cannot exceed the client setting (command DB
`fadeSound`). **`setSoundVolume` does not exist** in the 2695-command DB; mark
UNKNOWN. Use `fadeSound`.

**Positional / 3D.** `playSound3D [filename, ...]` plays a *file* on every
network machine. Parameters: `soundSource` or `soundPosition`, `isInside`,
`volume`, `soundPitch`, `distance`, `offset`, `local`, `loop`; returns an id
(2.12+); stop with `stopSound`. Trap: an object argument uses AGL and sinks the
source; use `getPosASL`. Since 2.10 an `a3\...` filename needs a leading
backslash, but an addon sound file must NOT have one (command DB).
`say3D [from, sound]` plays a `CfgSounds` class on one object. One object can
say only one sound at a time; calls queue. It is **not JIP-synced**. Stop it by
deleting or killing the returned sound source. Use it for short-range, short
sounds with speed-of-sound simulation off. `createSoundSource "type"` creates a
`#dynamicsound` from a `CfgVehicles` class that points into `CfgSFX`; it **always
loops** (command DB).

**Config (config proves).** `CfgSounds` class `sound[] = {file, volume, pitch,
range, ...}` — the 4th number is the maximum audible range in metres
(`sounds_f/config.cpp:22`; Windturbine 120, Owl in `CfgSFX` 1000). `CfgSFX`
uses `sound0[]`, `sound1[]`, ... plus a `sounds[]` list (`sounds_f/config.cpp:503`).
`CfgEnvSounds` volume is a **formula** over engine variables
(`bin/config.cpp:14575`): `Rain` volume `"rain"`, `Sea` volume `"coast"`,
`Meadows` volume `"meadow*(1-rain)*(1-night)"`, `Wind` volume
`"(1-hills)*windy*0.5"`. `CfgEnvSpatialSounds` binds rain/cricket/wind sound
sets to model memory points (`sounds_f/config.cpp:1268`).

**Ceilings.** `say3D` is one sound per object, queued and not JIP-synced.
`createSoundSource` always loops. `playSound3D` volume obeys the client setting.
`sound[]` range is fixed per class.

---

### 6. Ceilings summary

| Area | Ceiling | Evidence |
|---|---|---|
| Time | `skipTime` ±1000 h/skip since 2.10; `setTimeMultiplier` 0.1–120 | command DB |
| Time | No event fires on a time jump; `time` does not jump | command DB (no such EH) |
| Weather | `setRain`/`setOvercast`/`setFog` client-local and temporary | command DB |
| Weather | rain needs overcast >= 0.7 (BIKI) / 0.5 (A3) | BIKI / command DB |
| Weather | automatic change interval >= 90 min | command DB |
| Terrain | cell size and heightmap resolution baked in WRP | `getTerrainInfo`, BIKI |
| Terrain | `setTerrainHeight` cell-rounded, JIP-queued, savegame-lossy; artifacts | command DB |
| Map | contour geometry + interval engine-derived (colour only) | prior ADR-029/030 |
| Map | object-to-icon routing engine-internal | T157884 |
| Map | satellite raster baked per world | prior research |
| Markers | global commands broadcast whole marker state | command DB |
| Sound | `say3D` one per object, queued, not JIP-synced | command DB |
| Sound | `createSoundSource` always loops | command DB |
| Sound | final volume = client setting × scripted volume | command DB |

---

### Sources

- Command DB: `the acemod database entry <name>.yml` (v2.22). Files used:
  `time`, `skipTime`, `setDate`, `setTimeMultiplier`, `setAccTime`, `setOvercast`,
  `setRain`, `setFog`, `forceWeatherChange`, `nextWeatherChange`, `setWindStr`,
  `setWaves`, `humidity`, `getTerrainInfo`, `getTerrainHeight`, `setTerrainHeight`,
  `createMarker`, `allMapMarkers`, `setMarker*`, `setMarkerDrawPriority`,
  `drawLine`, `playSound`, `playSound3D`, `say3D`, `createSoundSource`, `fadeSound`,
  `playMusic`.
- BIKI (Wayback, 2024): `https://web.archive.org/web/2024/https://community.bistudio.com/wiki/getTerrainInfo`
  (array format, Altis/Stratis values).
- Shipped configs: `the derapified core engine config (Dta/bin.pbo)` (CfgWorlds:14967,
  Grid:16403, CfgEnvSounds:14575, CfgMarkers:14778);
  `the derapified map_altis.pbo config` (Altis:41, Grid:2326, weather:463,
  HDRNewPars:473, worldName:2284).
- Ground-truth functions: `functions_f/Map/fn_mapGridSize.sqf`,
  `functions_f/Map/fn_mapSize.sqf`, `functions_f/Environment/fn_setRain.sqf`;
  `sounds_f/config.cpp:22,503,1268`.
- Prior AEE research: `topo-map-surface.md`,
  `arma-map-grid-semantics.md`, `engine-config-surface.md`.
- WRP magic: `the Altis world file (Altis.wrp)` header `OPRW`.

## Engine reference — AI, mobility, physiology, armour, radio, wildlife, maritime, effects

Scope: the remaining AEE domains. Read-only research. Source order: the structured command DB
(`the acemod database entry <name>.yml`, acemod/arma3-wiki dist v2.22; parsed to
`the parsed command database`), the derapified engine core
`the derapified core engine config (Dta/bin.pbo)` (from `Dta/bin.pbo`), the unpacked PBOs under
`the unpacked engine PBOs`, and the game install `the Arma 3 install`.
Labels used: **BIKI says** (command DB, community-maintained documentation), **engine proves**
(config or script source read here), **community-reported**, **UNKNOWN**.

---

### 1. AI

**Behaviour model.** `setBehaviour` sets per-unit behaviour for every unit in a group. It does
**not** set the AI group behaviour; use `setCombatBehaviour` (2.4) or `setBehaviourStrong` (1.92)
for that (command DB). `setCombatMode` sets the *group* engagement rule
(BLUE/GREEN/WHITE/YELLOW/RED); `setUnitCombatMode` (2.2) sets one unit (command DB).
`setSpeedMode` takes UNCHANGED/LIMITED/NORMAL/FULL and always acts on the unit's group
(command DB).

**Movement and waypoints.** `doMove` orders a unit to a position. A non-leader unit is ordered
back into formation on arrival, so call `doStop` to hold it (command DB). `commandMove` is
identical except it plays a radio message; on a remote unit the message plays but the unit does
**not** move (command DB, MP note). `addWaypoint` places the point randomly inside the radius;
since 1.90 the position is more exact (command DB). `setWaypointPosition` with radius 0 can still
be off centre; a **negative radius** forces the exact position (command DB). Waypoint activation
fields (`setWaypointType/Speed/Behaviour/CombatMode/Formation`) switch group state when the
waypoint becomes active. `setWaypointStatements` runs its condition with `this` = group leader and
`thisList` = the group's units (command DB).

**Skill.** `setSkill` interpolates each sub-skill into a range in `CfgAISkill`. The engine core
proves the bands are four-element arrays `{min,min,max,max}` for `aimingAccuracy`, `aimingShake`,
`aimingSpeed`, `endurance`, `spotDistance`, `spotTime`, `courage`, `reloadSpeed`, `commanding`,
`general` (`config.cpp:331`). `setUnitAbility` accepts values above 1 but the engine caps the
actual ability (command DB). The AI Level coefficient, set by difficulty, rescales via
`skillFinal` (command DB).

**Sensing.** `knowsAbout` requires `who` to be local; the target may be remote. Knowledge resets
to zero beyond the view distance and after 120 s without sight. Neither fog nor daylight affect it.
The "magic number" a unit needs before it fires is 0.105 in Arma 3 (command DB). `reveal` is
**local**: `targetKnowledge`/`knowsAbout` update only on the PC that runs it (command DB, MP note).
`targets` returns a unit's target list, excluding itself. `setTargetAge` marks a target as seen
`age` seconds ago. Sensors and datalink are separate: `reportRemoteTarget`, `setVehicleReportOwnPosition`,
`confirmSensorTarget`, `listVehicleSensors` (command DB, Sensors group).

**Brains.** The engine core proves `CfgBrains` holds `DefaultSoldierBrain`,
`DefaultCivilianBrain` and `DefaultAnimalBrain`. The soldier brain exposes
`AIBrainAimingErrorComponent`, `AIBrainCountermeasuresComponent` (reaction time 0.1–3.0 s,
`randomReactionTimePercent` 0.3), `AIBrainSuppressionComponent` and
`AIBrainTargetSelectorComponent` (`config.cpp:2019`). These are config classes; a mod can add or
retune components but cannot replace the solver.

**Tasks.** `BIS_fnc_taskCreate` is engine script at
`the shipped functions_f Tasks/fn_taskCreate.sqf`. Parameters:
`[owner, taskName, texts, destination, state, priority, showNotification, taskType, alwaysVisible]`.
It defers to `BIS_fnc_setTask`. The whole task suite lives in `functions_f/Tasks/`.

**Locality.** `disableAI` is peculiar (command DB, MP note): the disable is stored **locally** and
applies while the unit is local. If the unit changes locality, re-run the command there.
`enableAI` re-enables a feature. `AEE` must treat every AI command as locality-sensitive.

---

### 2. Mobility

**Velocity and orientation.** `setVelocity` sets the velocity vector in m/s; since A3 each
component is clamped to **±5000 m/s** (command DB). `setVelocityModelSpace` is the same in model
space. `setVelocityTransformation` interpolates position, velocity, `vectorDir` and `vectorUp`.
The velocity term "does not do much in SP, but in MP ... helps the engine to figure out the next
position ... on other clients" (command DB). So for MP movement, supply the correct velocity.
`setDir` sets heading but **resets the object's velocity and `vectorUp`** (command DB).
`setVectorDirAndUp` sets orientation from two vectors. For an attached object the axes are relative
to the parent (model space).

**Physics (PhysX).** `setMass` and `setCenterOfMass` accept a gradual-change time; zero is
immediate (command DB). The PhysX group also holds `addForce` (one-frame impulse), `addTorque`,
`attachChild`/`detachChild` (PhysX joint, 2.22), `awake` (wake or sleep a body; also re-ragdolls a
corpse), `disableBrakes`, `getMass`, `getCenterOfMass` (command DB).

**Simulation tags.** `enableSimulation` disables animation and physics **locally**; the entity can
still take damage and report enemies. `enableSimulationGlobal` (1.12) is the global, JIP-safe
form (command DB). Dynamic Simulation operates on **groups**, not units, and never on a group that
contains a player or on mines (command DB, `enableDynamicSimulation`).

**Vehicles.** The engine core proves `simulation="ship"` on the `Ship` base
(`config.cpp:6983,7000`). Aircraft handling is config-only; the core declares `aileronSensitivity`
and `elevatorSensitivity` (`config.cpp:6882`). There is **no** `setFlightModel` command
(`commands.json`: the string does not occur). The flight model is therefore a hard ceiling (see
section 9).

**Flight and driving.** `flyInHeight` sets altitude above ground; default 100 m, minimum 20 m,
and "helicopters and planes won't evade trees and obstacles on the ground" (command DB).
`flyInHeightASL` sets a minimum ASL; the engine uses the higher of the two (command DB).
`setCruiseControl` (2.6) works **only** on CarX/TankX/ShipX simulation vehicles. It uses a PID
controller and "should only be called to change values and not ... every frame, as it resets the
PID controller" (command DB). `setDriveOnPath` works only on land vehicles that carry an AI
steering component; it never works on air vehicles or boats, and the unit must be stopped first
(command DB). `forceSpeed` has no effect on players (command DB).

---

### 3. Physiology

**Stamina.** `setFatigue` sets fatigue 0–1. `getFatigue` reads it. `enableStamina` toggles the
system. `setStamina` sets stamina seconds until depletion (all command DB, Stamina System group).
`setAnimSpeedCoef` sets an animation speed coefficient (0.5 = half speed) and joins the stamina
group (command DB).

**Damage state.** `setDamage` sets object/unit damage. `damage` reads it. `setUnconscious` (and
since 1.64) puts a unit into the incapacitated state; `lifeState` then reads "UNCONSCIOUS" or
"INCAPACITATED" (command DB). There is **no** `setBleeding`/`setWound` command in the engine DB
(`commands.json`: absent). Bleeding and wounds are **ACE3 medical** domain, reached through the
ACE3 API (`github.com/acemod/ACE3`), not the engine. AEE `compat_ace3` must map onto that API.

---

### 4. Armour, hit points, materials, surfaces

**Hit points.** `setHitPointDamage` sets one Hit Point by config class name; it has **no effect
when `allowDamage` is false** (command DB). `getHitPointDamage` reads it. `setHit`/`getHit` work
by selection name instead of Hit Point; `setHitIndex`/`getAllHitPointsDamage` (1.50) cover the
indexed set (command DB). `setVehicleArmor` sets armour 0–1 and is **inverted** relative to
`setDamage`: 1 is full health (command DB).

**Config-driven model.** The engine core proves the armour fields live on `CfgVehicles`: `armor`,
`armorLights`, `armorStructural`, `crewVulnerable`, `damageResistance`, and `class HitPoints`
(`config.cpp:4650` region; `HitPoints` classes at 5217, 5517, 5765, 5958, 6182, 6652, 7051, 7179,
7711). Ammunition carries `hit`, `indirectHit`, `indirectHitRange`, `typicalSpeed`
(`CfgAmmo`, `config.cpp:2429`). Blast falloff is `CfgDamageAround` (`radiusRatio`,
`indirectHit`; `config.cpp:4020`). A mod can retune these numbers and add Hit Points, but it
cannot replace the damage solver.

**Materials and surfaces.** `setObjectMaterial` sets a material on a selection. The selection
index comes from the vehicle's `hiddenselection[]` array, starting at 0 (command DB).
`setObjectMaterialGlobal` (1.54) does it network-wide. `CfgMaterials` (`config.cpp:2074`) holds
`Water` and the shader stacks. `surfaceType` returns the ground surface class at a position; it
returns the ground type **even under buildings and roads** (command DB). `CfgSurfaces`
(`config.cpp:10231`) holds `friction`, `rough`, `maxSpeedCoef`, `soundEnviron` and `impact` per
surface.

**Sound controllers.** `getCustomSoundController` (1.86) reads a controller; `setCustomSoundController`
writes one. These feed "simple expressions in config" (command DB); this is the reachable hook for
speed- or state-driven engine sound.

---

### 5. Radio

`sideRadio`, `groupRadio` and `globalRadio` play a `CfgRadio` sound. All three play **only on the
PC where the command runs**; broadcast needs `remoteExec` (command DB). The unit needs a radio
item such as `ItemRadio`, and the item must carry the radio property in `CfgWeapons` (command DB).
If the transmitting unit dies the transmission is interrupted; if the receiver dies it continues
(command DB). `CfgRadio` is declared in `description.ext` or mod config; the engine proves an
example at `the derapified missions_f_heli config` (`sound[]` and `title`).

`enableRadio` disables the on-screen radio message display; the AI still obeys orders
(command DB). `setSpeaker` (1.2) sets the voice. Its MP note warns that it "needs to run on every
computer with exactly the same arguments, otherwise the speaking unit could appear silent on other
PCs" (command DB). Custom channels exist: `radioChannelCreate` (50 slots), `customRadio`,
`customChat`, `radioChannelAdd/Remove` (command DB, Custom Radio and Chat group).

**Third-party radios.** ACRE2 and TFAR replace the engine radio with their own systems and expose
their own APIs. AEE `compat_acre2` uses an ACRE2 signal-strength callback; `compat_tfar` scales
TFAR range. The engine radio commands do not drive those APIs. Cite the ACRE2 repository
(`github.com/IDI-Systems/acre2`) for its API. The exact function names are **UNKNOWN** here and
must be read from the addon.

---

### 6. Wildlife and agents

**`createAgent`.** Creates an agent of a type. The command DB states: "An agent does not have a
group or leader or the standard soldier FSM associated with it — for instance, an enemy soldier
spawned as an agent has limited AI and will do nothing when fired upon — which can be useful to
limit the amount of AI processing being done in a mission with very large numbers of AI. Animals
are also commonly created as agents" (command DB). So an agent is cheap but nearly brain-dead;
`selectPlayer` onto an agent gives a player control (command DB). `agents` returns the mission's
agents. `deleteVehicle` cannot delete terrain objects or players, and actual deletion happens the
next frame (command DB).

**Animal config.** The engine proves the base class: `Animal: Man`, then `Animal_Base_F: Animal`
with `simulation="animal"`, `aiBrainType="DefaultAnimalBrain"`, `agentTasks[]={"AnimalMainTask"}`,
`moves="CfgMovesAnimal"` (`the derapified animals_f config:43,47`).
`CfgMovesAnimal` is defined there (`:1303`). `AnimalMainTask` points to
`\A3\animals_f\Data\scripts\main.fsm` and a condition script (`:1476`). `CfgBrains` gives
`DefaultAnimalBrain` empty components (`config.cpp:2019`), so animals run a small FSM only.

**Engine helpers.** There is no `BIS_fnc_spawnAnimal`; the wild-side helpers are
`functions_f/Ambient/fn_animalRandomization.sqf` and `fn_animalBehaviour.sqf`. Editor animal sites
spawn through `modules_f/sites/functions/fn_animalSiteSpawn.sqf` and
`modules_f/sites/site_inits/animal_*.sqf` (engine script, read here).

**`animalsEnabled`.** Not a command in the DB. Mark **UNKNOWN**; the world config controls animal
presence by default.

---

### 7. Maritime

The engine proves the boat base: `class Ship: AllVehicles` with `simulation="ship"`, `safeDepth`,
`waterAngularDampingCoef`, `periscopeDepth`, `ShipSteerCoef`, `verticalTurnCoef`, `maxSpeed`
(`config.cpp:6983`). `CfgMaterials>>Water` holds the water shader and ambient/diffuse values
(`config.cpp:2074`). `waves`/`setWaves` (Environment group) read and set wave amplitude
(command DB). There is no "buoyancy" command: a mod changes boat behaviour through
`setVelocity`, `setCenterOfMass`, mass, and config. `setDriveOnPath` never works on boats
(command DB). Wave geometry is world config (`CfgWorlds`). AEE must drive maritime state through
these hooks, not through a buoyancy API.

---

### 8. Effects and environmental sound

**Particles.** `CfgCloudlets` (`config.cpp:3585`) defines every particle effect. Scripts drive it
with `setParticleClass` (name a `CfgCloudlets` class), `setParticleParams` (override fields),
`setParticleCircle` (2.22 can override `onSurface`), and `setParticleFire` (command DB). `CfgLights`
(`config.cpp:4225`) holds light classes; `setLight*` commands (30 in the Lights group) control
them.

**Sound.** `CfgSFX` is in `the derapified sounds_f config, line 503` (engine script,
read here); `CfgEnvSpatialSounds` is at `:1268`; `CfgEnvSounds` is at
`the derapified core engine config (Dta/bin.pbo), line 14575` (per-mask beds such as Rain, Sea, Meadows, Trees,
each with a `volume` expression). These are the reachable environmental-sound hooks.

**Crew.** `createVehicleCrew` (0.76) creates crew for a vehicle's faction, reusing the existing
group if present (command DB).

---

### 9. Engine ceilings (what a mod cannot change)

Each claim below is supported by the engine source or the command DB.

1. **Flight model.** No `setFlightModel` command exists; the model is config-only
   (`aileronSensitivity`, `elevatorSensitivity`, `config.cpp:6882`). AEE's momentum-theory lift
   model computes its own state but cannot replace the engine's flight dynamics.
2. **Damage model.** Armour, Hit Points and blast falloff are config data (`config.cpp:4650`
   region, 2429, 4020). A mod can retune or extend them but cannot install a new solver. Hit Point
   changes also stop when `allowDamage` is false.
3. **AI.** The AI plan/solve loop is engine-internal; a mod only sets behaviour, skill, waypoints
   and knowledge. `setSkill` is clamped by `CfgAISkill` bands and `setUnitAbility` is capped
   (command DB). FSM and brain components are data, not replacement code.
4. **Agents.** An agent has no soldier FSM and "will do nothing when fired upon" (command DB), so
   agent AI cannot be raised to soldier standard. This is also the performance ceiling for large
   creature counts.
5. **Locality and MP.** `reveal`, `disableAI`, `enableRadio`, `sideRadio`, `groupRadio`,
   `globalRadio` and `setSpeaker` are local or need identical execution everywhere (command DB).
   `setVelocity` in MP needs a correct velocity term to keep other clients smooth (command DB).
6. **Radio protocol.** ACRE2 and TFAR own their APIs; the engine radio commands do not reach them.

---

### 10. Quick rule list for AEE

- AI: `setBehaviour` is per-unit; use `setCombatBehaviour`/`setBehaviourStrong` for groups.
- AI: re-run `disableAI` after a locality change; `reveal` updates only the executing PC.
- Mobility: `setDir` clears velocity and `vectorUp`; `setVelocity` clamps at ±5000 m/s.
- Mobility: `setCruiseControl` only CarX/TankX/ShipX, never per frame; `setDriveOnPath` land only.
- Physiology: no engine bleeding/wounds command; use the ACE3 medical API.
- Armour: `setHitPointDamage` obeys `allowDamage`; `setVehicleArmor` is inverted (1 = full health).
- Radio: engine radio plays locally only; ACRE2/TFAR need their own API.
- Wildlife: agents are cheap but have no soldier FSM; set animal behaviour through config and the
  ambient functions.
- Maritime: no buoyancy command; use velocity, mass and centre of mass plus world config.
- Effects: particles come from `CfgCloudlets`; environment sound from `CfgEnvSounds`/
  `CfgEnvSpatialSounds`/`CfgSFX`.

**Sources.** Command DB: `the acemod database entry <name>.yml` (acemod/arma3-wiki dist
v2.22), parsed `the parsed command database` and `raw-commands.md`. Engine config:
`the derapified core engine config (Dta/bin.pbo)` (derapified from `Dta/bin.pbo`), with line numbers as
given. Animal config: `the derapified animals_f config`.
Sound config: `the derapified sounds_f config`. Engine scripts:
`the unpacked functions_f scripts` and `.../modules_f/`. Prior surface map:
`engine-config-surface.md`.

## Part 3 — Consolidated ceilings

### What a mod cannot do, and why

This is the consolidated list. Each entry gives the evidence. The evidence
source is named: `bin.pbo` and `ui_f` line numbers are from the derapified
engine config on this machine; ADR numbers are in AEE `docs/adr/`; feedback
numbers are Bohemia Interactive feedback tracker IDs.

#### 3.1 Simulation and physics

| Ceiling | Evidence |
|---|---|
| The simulation solver and the ballistic integrator are engine code. A mod sets the start state in `CfgAmmo` and the engine integrates. There is no integration hook. | ADR-017. `bin.pbo` `CfgAmmo` at line 2429 sets `airFriction`, `initSpeed`, `typicalSpeed`. The engine steps them. |
| Vehicle flight dynamics cannot be swapped at run time. There is no `setFlightModel`. `mass` and `maxSpeed` load at mission load. | ADR-017. `CfgVehicles` at `bin.pbo:4593`. |
| The physics engine is PhysX. A mod tunes mass, centre of mass, and config, but cannot add a simulation step or a custom constraint solver. | `bin.pbo` PhysX config block. |

#### 3.2 Rendering and post-process

| Ceiling | Evidence |
|---|---|
| Materials resolve at load. A mod cannot add a custom shader or swap a PAA at run time. | ADR-027. |
| The post-process effect set is fixed. `ppEffectCreate` accepts only the named effects. | acemod DB `ppEffectCreate.yml`: "Supporting effects" lists exactly nine. |
| Two post-process effects should not share a priority. The DB claims the second `ppEffectCreate` fails and returns -1. Measured on this build it does NOT: two modules both received the SAME positive handle (32) at priority 2000 (AEE RPT, `optics/FilmGrain` and `nightvision/FilmGrain`). A mod must track its own handles and compare, not trust the return value. | `ppEffectCreate.yml`; AEE RPT 2026-10-08 (`sec-render.md`). |
| Depth of field is usable but is not one of the listed `ppEffectCreate` effects. It is reached through `CfgWorlds >> DOFPars` and camera commands. | AEE `tools/arma3-wiki/README.md`; `sec-render.md`. |
| `LightShafts` and `HBAOPlus` cannot be created with `ppEffectCreate`. The set is closed. | `sec-render.md`. |
| The particle count is capped by the client `particlesQuality` setting. A mod cannot raise it. | `sec-render.md`. |
| The engine has one thermal-radiance model. A mod cannot replace it. | `sec-render.md`. |
| `RscMapControl` render fields are config, but contour geometry and interval are engine-derived. | ADR-029. See 3.4. |

#### 3.3 Thermal, night vision, optics

| Ceiling | Evidence |
|---|---|
| The engine holds two thermal palettes only, WHOT and BHOT. A mod cannot add a palette. | ADR-029; thermal work. |
| `setAperture` and `setApertureNew` interact. `setAperture` forces `setApertureNew [v,v,v,1]`. Run `setApertureNew` after `setAperture`. A value of 0 or less means automatic. Higher is darker. | AEE memory: "ARMA 3 APERTURE DIRECTION CONVENTION"; BIKI `setAperture` via Wayback, Namikaze note. |
| Vanilla HDR eye-adaptation constants are fixed in `CfgWorlds >> HDRNewPars`. They are config, so a mod can change them, but only per world. | Altis `config.cpp:562-598`: `eyeAdaptFactorLight=3.3`, `eyeAdaptFactorDark=0.75`. |

#### 3.4 Map and symbology

| Ceiling | Evidence |
|---|---|
| Object-to-icon routing is engine-internal. The engine decides which map icon a world object uses. | ADR-029; feedback T157884. |
| `CfgLocationTypes >> drawStyle` is a fixed engine enum. An unknown value logs "Wrong location draw style". | ADR-029; `ui_f` `CfgLocationTypes` at line 81444. |
| Contour geometry and the contour interval are engine-derived. Only the colour and the `showCountourInterval` label are config. | ADR-029. Note BI spells the field `showCountourInterval` (typo). |
| The satellite raster is baked per world. `pictureMap` and the blend fields tune it, they do not replace it. | ADR-029. |
| There is no hypsometric tint ramp field. | ADR-029; `engine-config-surface.md`. |
| The engine stretches a marker texture to the marker box. It does not preserve aspect. | Feedback T170754. |
| The engine map legend class cannot hold a body. A mod scripts its own legend. | ADR-029 (AEE scripts the MGRS overlay). |
| `colorForestTextured` reaches only the Eden `ctrlMap`, not the base `RscMapControl`. | ADR-029. |
| `shadedSea` is not declared in the vanilla base `RscMapControl`. | ADR-029. |
| `colorGrid` is the colour of the edge grid numbers. `colorGridMap` is the in-map lines. Alpha-zero on `colorGrid` hides the numbers, not just lines. | Open-sourced `BohemiaInteractive/CWR` `engine/Poseidon/UI/Map/UIMap.cpp` `CStaticMap::DrawGrid()` lines 1971-2042. |
| Terrain heightmap, satellite raster, and contour geometry are map data, not config. | ADR-029; `engine-config-surface.md`. |
| Terrain height is grid-cell aligned. `setTerrainHeight` is server-only and causes visual artifacts at extremes. | acemod DB `setTerrainHeight.yml`; AEE map work. |

#### 3.5 Animation

| Ceiling | Evidence |
|---|---|
| Animation motion is asset-gated. A config value change alters timing, not a missing `.rtm`. | ADR-029. |
| Some animation commands are local only and need `remoteExec`. | acemod DB `switchMove.yml`, `playMove.yml`. |

#### 3.6 Fonts and UI

| Ceiling | Evidence |
|---|---|
| A font family in `CfgFontFamilies` is inert until the `.fxy` and glyph PAAs ship. | ADR-029; AEE font work. |

#### 3.7 Lighting

| Ceiling | Evidence |
|---|---|
| `CfgLights` loads once. A mod cannot add a per-object light at run time. | `engine-config-surface.md`; `bin.pbo` `CfgLights` at line 4225. |

#### 3.8 Network and JIP

| Ceiling | Evidence |
|---|---|
| `publicVariable` broadcasts a declared `missionNamespace` variable and its value to all. It cannot carry scripts, displays, or `createVehicleLocal` objects. The wiki gives no byte limit, only "keep it small". The exact size is UNKNOWN. | acemod DB `publicVariable.yml`; BIKI Multiplayer Scripting. |
| `publicVariableClient` values do NOT re-sync when a JIP client reconnects. Only a server `publicVariable` re-syncs. | `sec-net.md`; BIKI Multiplayer Scripting. |
| JIP clients re-run every `init` field and every client-side event script. State set only at mission start is lost unless it is re-sent or made persistent. | BIKI Multiplayer Scripting. |
| JIP message order is not guaranteed. A repeated JIP id overwrites the previous message. | `sec-net.md`. |
| `remoteExec` runs functions scheduled and commands unscheduled. `remoteExecCall` forces unscheduled. | acemod DB `remoteExec.yml`, `remoteExecCall.yml`. |
| `CfgRemoteExec` filters clients only. The server is exempt. The mission file overrides the campaign, which overrides the game. | `sec-net.md`; BIKI Remote Execution. |
| `BIS_fnc_MP` is deprecated. Use `remoteExec` or `remoteExecCall`. | acemod DB; engine stub `functions_f/initFunctions.sqf:22`. |
| The 36 commands in the DB group "Broken Commands" are non-functional or deprecated. They must not be used. | acemod DB group `Broken Commands`; see `raw-notes.md`. |

#### 3.10 AI, mobility, physiology, radio, wildlife, maritime

| Ceiling | Evidence |
|---|---|
| There is no `setFlightModel`. The flight dynamics model is config-only (`aileronSensitivity`, `elevatorSensitivity`). | `bin_raw/bin/config.cpp:6882`; `sec-domains.md`. |
| The damage model is config-driven. A mod can extend it, not replace it. `HitPoints`, `CfgAmmo` blast, and `armor` are data. | `sec-domains.md` (`sec-domains.md` cites `config.cpp:4593`, `4020`). |
| There is no engine bleeding or wound model. `setBleeding` and `setWound` do not exist. ACE3 medical owns them. | `sec-domains.md`; not in the 2695-command DB. |
| `createAgent` gives no soldier FSM. It does nothing when fired on. Animals use `CfgMovesAnimal` and `DefaultAnimalBrain`. | `sec-domains.md`; `animals_f/config.cpp:43,47,1303,1476`. |
| There is no radio-protocol interception. `sideRadio`, `groupRadio`, `globalRadio` play only on the executing PC. | `sec-domains.md`. |
| There is no buoyancy command. Ships use `simulation="ship"`. | `sec-domains.md`; `config.cpp:6983`. |
| `setVehicleArmor` is inverted. 1 is full health, 0 is destroyed. | `sec-domains.md`. |
| `setVelocity` clamps at plus or minus 5000 m/s. | `sec-domains.md`; command DB. |

#### 3.11 Command gotchas that are not full ceilings

- `diag_deltaTime` inside a slow PFH under-integrates. The measured AEE case is
  a 0.1 s PFH, roughly 8x low. (AEE RPT, 2026-10-08.)
- `setTimeMultiplier` is capped at 0.1 to 120. (`setTimeMultiplier.yml`.)
- `skipTime` is capped at plus or minus 1000 hours per call since 2.10. Use
  `setDate` for large jumps. (`skipTime.yml`.)
- `createSoundSource` always loops. (`createSoundSource.yml`.)
- `createAgent` cannot use the gear screen for a player, and differs from
  `createUnit`. (`createAgent.yml`.)
- `ctrlDelete` inside the control's own event handler crashes the game.
  (`ctrlDelete.yml`.)
- Config class names are case-insensitive. `Church` and `church` are the same
  class. (`engine-config-surface.md`, hemtt L-C03.)
- `setSoundVolume` does not exist in the 2695-command DB. Use `fadeSound`. The
  final volume is the client setting times the scripted value. (`sec-world.md`.)
- No engine event fires on a time jump. `skipTime` and `setDate` move `daytime`
  and the sun instantly, and `time` itself does NOT jump. A driver that samples
  scene luminance must store a world clock (`daytime` or `date`) and detect the
  discontinuity. (`sec-world.md`; command DB.)
- `cameraEffectEnableHUD` defaults off, so `drawIcon3D` is invisible through a
  custom camera until it is enabled. `camDestroy` does not terminate the effect;
  call `cameraEffect ["terminate", ...]` first. (`sec-render.md`.)

## Part 4 — Sources

Primary:

- BIKI (Bohemia Interactive Community Wiki), `https://community.bistudio.com/wiki/`.
  Read through the Wayback Machine because the live wiki returns HTTP 403:
  `https://web.archive.org/web/2024/https://community.bistudio.com/wiki/<Page>`.
  Pages read this way include `setAperture`, `drawLine`, `drawIcon`, `skipTime`,
  `setTimeMultiplier`, `publicVariable`, `remoteExec`, and `Multiplayer Scripting`.
- acemod/arma3-wiki, `dist` branch, data version 2.22,
  `https://github.com/acemod/arma3-wiki`. The structured command database
  (2695 commands) used throughout.
- RV/Poseidon engine source (Arma: Cold War Assault Remastered), the direct
  Arma ancestor, `https://github.com/BohemiaInteractive/CWR`. Used to settle
  `RscMapControl` grid semantics (`engine/Poseidon/UI/Map/UIMap.cpp`).
- CBA_A3, `https://github.com/CBATeam/CBA_A3`. Used to prove the per-frame
  handler timing (`addons/common/fnc_addPerFrameHandler.sqf`).
- ACE3, `https://github.com/acemod/ACE3`. Used for advanced ballistics and the
  medical model that replaces the engine bleeding model.

Shipped content read on this machine (read-only):

- Game install: `the Arma 3 install` (Dta/bin.pbo,
  Addons/*, map PBOs).
- Unpacked ground truth: `the unpacked engine PBOs` (functions_f 1139 SQF,
  modules_f, data_f, anims_f, ui_f, sounds_f).
- Derapified engine config: `the derapified core engine config (Dta/bin.pbo)` (37418 lines)
  and `the derapified ui_f.pbo config`.
- Extracted map config: `the extracted Altis world` (Altis.wrp and
  config.cpp).

Prior AEE research reused (read-only):

- `engine-config-surface.md` (engine roots, line numbers, ceilings).
- `arma-map-grid-semantics.md` (map grid colour fields).
- `topo-map-surface.md`,
  `the Arma map-surface research note`.

Database extracts produced for this task:

- `the parsed command database` — parsed 2695 commands.
- `the grouped command list` — all commands grouped.
- `the command gotcha notes` — 36 broken commands, 563 embedded
  notes, 107 multiplayer notes.
