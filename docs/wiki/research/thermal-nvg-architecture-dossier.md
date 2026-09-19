# Arma 3 Thermal / NVG Realism — Research Dossier

**Purpose:** ground truth on (1) how real thermal and image-intensification sensors behave, and (2) how Arma 3's Real Virtuality 4 (RV4) engine actually renders "Ti" (thermal) vs "NVG" vision, so a coding agent can plan a realistic thermal mod without re-discovering the engine's hard walls by trial and error.

**Headline finding, stated up front because it answers the specific bug report:** Arma 3's native thermal render pass is a compiled, non-interceptable renderer. It is architecturally different from NVG, which runs through the ordinary, moddable post-process (`ppEffect`) pipeline. This is not a misconfiguration on your end — it's why your NVG post-processing sticks and your thermal post-processing gets overwritten. Section 3 lays out the evidence and Section 5 lays out the two working architectures other mods use to get around it.

---

## 1. Real-world sensor physics

### 1.1 Thermal imaging (FLIR / thermal weapon sights / thermal binoculars)

**What it actually measures.** Everything above absolute zero radiates infrared energy in proportion to its temperature (blackbody radiation). Thermal imagers don't "see through" anything — they measure *surface* radiance in the mid-wave (MWIR, ~3–5 µm) or long-wave (LWIR, ~8–14 µm) bands and false-color it into a viewable image. A material's emissivity matters as much as its temperature: a hot polished metal surface can look cool because it reflects ambient thermal radiation rather than emitting its own (this is why aluminum reflects a thermal "mirror image" of whatever is facing it), while a matte, high-emissivity surface at the same physical temperature reads much hotter.

**Detector types:**
- **Cooled photon detectors** (InSb, HgCdTe/MCT) — respond to individual photons, need cryogenic cooling (Joule-Thomson/Stirling coolers) to suppress their own thermal noise, offer the best sensitivity and resolution, support longer/heavier optics, and are expensive with a multi-minute cooldown before use. Used in top-end targeting pods and high-end weapon sights.
- **Uncooled microbolometers** (amorphous silicon/VOx) — a resistive grid that changes resistance with absorbed IR heat, room-temperature operation, instant-on, cheap, compact, lower sensitivity/resolution than cooled. This is what's in nearly all consumer and most infantry thermal monoculars/weapon sights today.

**Sensitivity spec:** NETD (Noise Equivalent Temperature Difference) — the smallest temperature difference the sensor can resolve above its own noise floor. Lower NETD = cleaner, more detailed image. This is the real-world analog of "how noisy/grainy should my fake sensor look."

**Visual signature to replicate:**
- **Polarity palettes**: white-hot (hot = bright), black-hot (hot = dark), and colorized ramps (e.g., "Ironbow"). Human-factors research shows preference is scenario- and user-dependent — no universal "best," which is why real sights and Arma's own engine both expose a palette *toggle* rather than one fixed scheme.
- **Native resolution is low and heavily upscaled** — infantry thermal sensors are commonly 160–640 px wide; the smooth/blurry, low-detail look of real thermal footage is a resolution/optics artifact, not just a filter.
- **Blooming/bleed around hot points** — muzzle flash, hot brass, exhaust, and engine blocks bloom and smear into neighboring pixels; edges of hot objects are soft, not crisp.
- **Glass blocks it.** Ordinary window/vehicle glass absorbs MWIR/LWIR — a person behind a window is invisible in true thermal (this is a full stop, not a partial reduction). This is a well-documented physics demo and a real tactical fact (thermal can't see through glass; visible/NIR-based NVG can).
- **Thermal crossover** — at points in the diurnal cycle where a target and its background pass through the same temperature (commonly dawn/dusk, or a hot pavement cooling toward body temperature after sunset), thermal contrast collapses and targets can become genuinely invisible. This is a real, well-studied limitation, not a bug — worth deliberately reproducing rather than "fixing."
- **Weather:** LWIR penetrates light fog/smoke/rain somewhat better than visible light, but it is not X-ray vision and is still significantly degraded by heavy obscurants and by any solid, non-radiating barrier.

**Reference hardware to anchor visual targets on:** AN/PAS-13 (TWS family), Trijicon IR-Hunter/REAP-IR, Pulsar Trail/Thermion (consumer-grade uncooled LWIR riflescopes — closest match to most infantry TWS look), and cooled MWIR targeting pods on aircraft (higher resolution, longer range, the "AC-130/Predator guntape" look most people mentally associate with "thermal").

### 1.2 Image intensification (NVG / NODs)

This is a *completely different technology* from thermal — it amplifies existing visible/near-infrared light rather than measuring heat. Confusing the two (as many game "thermal" effects implicitly do) is itself a realism bug worth avoiding.

**The pipeline (image intensifier tube):**
1. Objective lens collects ambient light (starlight, moonlight, sky glow, active NIR illuminators).
2. A **photocathode** (modern tubes: gallium arsenide) converts photons to photoelectrons via the photoelectric effect.
3. Electrons accelerate into a **microchannel plate (MCP)** — a glass disc full of millions of microscopic channels held at ~5000V — where cascading secondary emission multiplies each electron thousands of times. This is the *gain* stage, and it is adjustable/auto-gated in real devices (auto-gain against bright light).
4. Amplified electrons strike a **phosphor screen**, which converts them back to visible light — traditionally green (P43), because the human eye discriminates more shades of green than any other single hue at low light and P43 was the historically available phosphor; white phosphor (P45) has become the modern special-operations standard for better depth perception, contrast, and reduced eye fatigue, while offering effectively identical low-light performance to green.

**Visual signature to replicate:**
- Monochrome (green or white), not full color.
- **Halo/bloom around bright point sources** (streetlights, muzzle flashes, IR lasers) — this is MCP saturation, a real optical artifact, not just a glow filter; it should intensify with scene brightness/gain, not be a fixed-size decal.
- **Scintillation** — random flickering bright specks, worse in very low ambient light or on lower tube generations; a form of photon-shot-noise made visible by the gain stage.
- **Fixed pattern noise / black spots** — faint honeycomb texture from the MCP structure and small manufacturing blemishes; static per-device, not per-frame animated noise.
- **~40° circular FOV** with real, physical fisheye-style edge softness/distortion from the objective lens (monocular PVS-14-class devices). Panoramic quad-tube systems (GPNVG-18) stitch multiple tubes for a much wider FOV.
- **No inherent magnification** (1x) — unlike thermal weapon sights, which commonly have variable digital/optical zoom.
- **Passes through ordinary window glass** (it's still visible/NIR light) — the inverse of thermal's behavior, and a useful discriminator if you want the two systems to feel mechanically distinct in-game.

**Reference hardware:** AN/PVS-14 (monocular, Gen 3), AN/PVS-31/BNVD (binocular), GPNVG-18 (panoramic quad-tube, ~97° FOV).

### 1.3 Fusion systems — the real-world version of exactly what you're proposing

This matters a lot for your design decision: **real militaries already build "thermal" as a composited overlay on a separate image-intensified base view**, not as a single unified sensor. The L3Harris **ENVG-B / AN/PSQ-20** helmet system literally fuses an I² (white-phosphor tube) image with a thermal microbolometer image and lets the operator blend between **I² only / thermal only / fused (overlay, outline, or full)**, with adjustable gain on each channel independently, at a 40° FOV. This is precedent, not a hack: your instinct to "take night vision as a second view and composite thermal-like data onto it" mirrors how actual fielded fusion goggles work, and is *more* physically honest than most games' single-channel "thermal vision mode."

---

## 2. How Arma 3 (Real Virtuality 4) actually renders vision modes

### 2.1 Three render states, three different pipelines

| State | Engine mechanism | Moddable via standard `ppEffect` pipeline? |
|---|---|---|
| **Normal** | Standard forward-rendered scene | Yes, fully |
| **NVG** (`visionMode "NVG"`, or goggles worn) | Baked NVG shader (green tint/gain/grain) **plus** the same `ppEffect` pipeline layered on top | Yes — `ppEffectForceInNVG` exists specifically so you can force an effect to keep applying while NVG is active |
| **Ti / thermal** (`visionMode "Ti"`) | A separate, compiled native thermal renderer that reads per-object material heat data directly | **No** — community testing (Bohemia Interactive Forums thread "Adding WetDistortion ppEffect to Thermal Imaging") confirms standard `ppEffectCreate` effects largely do not apply while the camera is in Ti vision. This is the load-bearing fact for your bug. |

### 2.2 The material-level thermal channel: RVMAT `StageTI`

Arma's material files (`.rvmat`) can carry a dedicated thermal stage:

```
class StageTI
{
    texture = "a3\data_f\default_vehicle_ti_ca.paa";
};
ambient[]       = {1,1,1,1};
diffuse[]       = {0,0,0,1};
forcedDiffuse[] = {0,0,0,0};
emmisive[]      = {0,0,0,1};
specular[]      = {0,0,0,0};
specularPower   = 0;
```

This is the actual "thermal texture" — a separate greyscale map (independent from the visible-light albedo/CO texture) that encodes how hot that surface reads. It is **per-object, per-material**, not a single global shader. This is almost certainly why your override is being "overwritten": every vanilla asset, and every other mod's assets, ship their own `StageTI` (or fall back to the engine default `a3\data_f\default_vehicle_ti_ca.paa`), and the native Ti renderer reads directly from whichever material is bound to the face on screen. There is no single hook point that lets you globally intercept "the" thermal image the way there is for `ppEffect`s in Normal/NVG — you would need to touch the RVMAT of every asset you want to affect.

Useful related render flag (declared alongside `NoColorWrite`, `NoAlphaWrite`, etc. in the RVMAT render-flags list): **`NoTiWrite`** — excludes a face from being written into the thermal buffer at all. This is the correct tool for making glass "block" thermal realistically (see §1.1) instead of relying purely on texture values.

### 2.3 The scriptable levers that *do* work — this is your actual legal surface

These are the only officially supported hooks into the native thermal pipeline. None of them let you replace the renderer; all of them let you feed it better data or reshape its output curve.

| Command | What it controls | Notes |
|---|---|---|
| `setTIParameter [paramName, value]` | Global display window over the raw thermal signal. Key params: `"OutputRangeStart"`, `"OutputRangeWidth"`. Formula: `output = OutputRangeStart + thermalValue * OutputRangeWidth`. | Can only **compress or offset** the existing signal — it cannot *stretch* contrast. True AGC-style auto-contrast-boost is not achievable this way. Use `getTIParameters` to enumerate all valid param names. Settings are **not saved** across a save/load and must be reapplied. |
| `vehicle setVehicleTIPars [engine, wheels, weapon]` | Per-vehicle heat state, each 0..1 (0 cold, 1 hot), independent of whether the part is actually "in use." | **Does not work on infantry weapons.** This is your main lever for making a cold vehicle warm up over time, or simulating a running engine, independent of the RVMAT's static texture. |
| `state setCamUseTI modeIndex` (0–7) | Selects one of the engine's baked palette LUTs for a `camCreate`'d camera that is the player's current main camera. | 0 White Hot · 1 Black Hot · 2 Light-Green-hot/Dark-Green-cold · 3 Black-hot/Dark-Green-cold · 4 Light-Red-hot/Dark-Red-cold · 5 Black-hot/Dark-Red-cold · 6 White-hot/Dark-Red-cold · 7 "shade of red/green, bodies white" (nicknamed "predator vision" in BI's own example). These are fixed, compiled LUTs — not shader source you can edit. |
| `"renderTarget" setPiPEffect [mode, ...params]` | Sets the visual effect applied to a **render-to-texture (RTT) surface**, independent of the player's own view. | 0 Normal · 1 Night Vision · 2 Thermal Imaging (native) · **3 Color Correction — fully custom, parametrized brightness/contrast/offset/blend/lerp/RGB-matrix** · 7/8 alt thermal (inverted / green) · 9–70 up to 64 more baked alt-thermal palettes (added in engine v2.10). **Mode 3 is the single most important lever in this whole document** — see §4.2 and §5. |
| `disableTIEquipment` | Disables TI-capable equipment outright (mission/scripting control) | |
| `getVehicleTIPars` / `getTIParameters` | Read-back counterparts of the above | |

CfgWeapons-level config keys (for optics/scopes that use native Ti directly):
```
class OpticsModes
{
    class TWS
    {
        visionMode[]  = {"Ti","Normal"};
        thermalMode[] = {0,1};   // toggleable white-hot/black-hot presets
        ...
    };
};
```

### 2.4 The gameplay-detection system is a separate thing entirely

Don't conflate the *rendering* pipeline above with Arma's AI/mission-logic **sensor system** (`CfgVehicles > Sensors > IRSensorComponent`, `irTargetSize`, engine-needs-6-seconds-running-to-register-hot / up-to-1-hour-to-cool-down, etc.). That's an abstract detection model for AI targeting and radar-like awareness — it doesn't drive what pixels get drawn, and fixing/tuning it won't touch your visual bug (and vice versa).

### 2.5 The capability ceiling by asset category

This is the honest limit of what's dynamically controllable today, gathered from Bohemia's scripting reference plus how the most complete existing thermal mod (A3TI, see §4.1) actually behaves in practice:

| Target | Dynamically controllable | Needs a shipped RVMAT | Engine-baked / immutable |
|---|---|---|---|
| **Terrain** | Only via the "second-sun" trick (see §4.1) | — | No runtime terrain-material swap exists at all; terrain heat is otherwise config-capped |
| **Static rocks** | Same second-sun trick only | — | Same as terrain |
| **Buildings** | `setObjectMaterial` per selection — *only if the model ships `hiddenSelections`* | cold/hot TI rvmat pair | Map-embedded statics with no hiddenSelections get sun-term only |
| **Vehicles** | **Full control**: `setVehicleTIPars` (3 heat slots) + per-selection material gradients + damage-state heat | per-selection rvmats | — |
| **Infantry** | Material swap per clothing selection (cloth → cold/hot texture; metal gear keeps native engine heat) | clothing TI rvmats | Base body renders natively at a fixed ~33°C skin temperature |
| **Vegetation** | Second-sun trick only | — | Fully engine-baked otherwise |

Practical takeaway: **vehicles are the highest-fidelity target for dynamic thermal work** because they're the only category with genuine per-component runtime control. Terrain/vegetation/rock heat is realistically a lost cause beyond the sun-term approximation — treat that as a documented engine ceiling, not something to keep chasing.

---

## 3. Direct diagnosis of "our thermal keeps getting overwritten"

Putting §2.1–2.3 together: you are very likely trying to layer custom `ppEffectCreate` post-processing (or a custom RVMAT swap on the player's viewmodel/screen) on top of the vanilla `visionMode "Ti"` render path, the same way your NVG mod successfully layers onto `visionMode "NVG"`. This will not work, because:

1. The Ti render path is a **separate compiled renderer**, not a shader you can substitute or a postprocess stack you can append to — this is stated explicitly by the two scriptable levers Bohemia exposes (`setTIParameter`, `setVehicleTIPars`) being the *entire* public surface for influencing it, plus corroborating community bug reports that `ppEffect`s don't apply while the camera is in Ti mode.
2. Even the thermal *image itself* is not one texture you can hook — it's computed live, per-face, from whatever `StageTI` each object's individual RVMAT provides. Vanilla assets and other mods' assets still carry their own StageTI data, so your override (unless you've patched every relevant RVMAT) is fighting a per-object data source, not a single global render target.
3. NVG has none of these problems because it's explicitly designed as a bolt-on: the engine renders its own green-tint/gain baseline, then runs the *normal* `ppEffect` pipeline on top, with `ppEffectForceInNVG` existing specifically to guarantee your effects survive the NVG state. There's no equivalent "ForceInTI" flag anywhere in the API, because the Ti pipeline was never designed to be extended that way.

This isn't a wrong-RVMAT-syntax problem or an engine bug you can patch around — it's the intended architecture. Every serious Arma 3 thermal mod (§4) works *around* this wall rather than through it.

---

## 4. What the best existing mods actually do (prior art)

### 4.1 A3TI — "Arma 3 Thermal Improvement"
The most complete community thermal overhaul (originally built for AC-130U gunship work, now a general-purpose standalone). It does **not** attempt to replace the native Ti renderer. Instead it:
- Runs a "Fusion" mode that layers thermal-style RVMATs on top of the standard **NVG** visionMode (confirmed by its own changelog language: "Tweaked Fusion RVMATS," "Tweaked Fusion Grain") — i.e., it uses the moddable NVG pipeline as the base, exactly the strategy this dossier recommends in §5.
- Approximates terrain/vegetation/building heating via a scaled "second sun" light source feeding the engine's native sun-heating term (a static brightness value of 13 in A3TI's implementation) rather than trying to author true per-pixel terrain heat, which the engine doesn't support at runtime.
- Uses a per-selection material-swap function (`fn_getThermalSelections`) to give infantry and buildings dynamic hot/cold appearance where the underlying model has `hiddenSelections` to swap.
- Ships default display-gain-style settings roughly analogous to `setTIParameter`'s `OutputRangeStart`/`OutputRangeWidth`.
- Adds MWIR white-hot/black-hot toggling, an IR/NV fusion mode, and a laser target marker system usable in Zeus and from targeting pods.
- Known limitation pattern worth noting: mod compatibility (RHS aircraft, modded tank driver seats) breaks specifically at the points where another mod's vehicle config doesn't expose the hooks A3TI needs — further evidence that everything here is config/selection-dependent, not a magic global override.

### 4.2 SkeetIR / REAPIR / the "PIP scope" technique — the technique most directly relevant to you
Several weapon-sight mods (SkeetIR, and the in-development REAPIR) sidestep the native Ti renderer for **scopes** entirely by using Arma's Picture-in-Picture (PIP) system:
1. Spawn a second, independent camera (`camCreate`) positioned/aimed through the scope's optical axis.
2. Route it to a render-to-texture surface: `cam cameraEffect ["Internal","Back","surfaceName"];`
3. Set that RTT surface's rendering mode independently of the player's own view with `"surfaceName" setPiPEffect [...]`.
4. Display the resulting texture on the scope's screen mesh (or an `RscPicture` UI control via `#(argb,512,512,1)r2t(surfaceName,1.0)`).

**Why this matters:** once that camera's output exists as an ordinary texture, it is no longer inside the gated Ti render pass — it's just pixels on a surface. You can then apply completely custom shader/material treatment to *that texture* (grain, bloom, edge-enhance, palette remap, scanlines, chromatic aberration, vignette) with none of the "ppEffects don't apply in Ti" restriction, because you're not asking the engine's live camera to run an effect during Ti — you're post-treating a texture after the fact.

You have two sub-options for the RTT camera's *base* image, and they trade off exactly the same way as your original instinct:
- **`setPiPEffect [2]`** (native thermal) as the base — you inherit the real, per-object `StageTI` heat data (so foliage/camouflage penetration behaves correctly), and then do your extra stylization on top of that already-rendered texture.
- **`setPiPEffect [0]`** (normal) or **`setPiPEffect [1]`** (NVG) as the base, then **`setPiPEffect [3]`** (Color Correction — a fully custom, scriptable brightness/contrast/offset/color-matrix transform) to fake a thermal-like palette from ordinary lit/unlit contrast — full stylistic freedom, zero engine-thermal restrictions, but it will not "see" real heat signatures (a camouflaged warm target won't pop the way it would with real StageTI data) since you're working from the visible-light image.

Community reports on the SkeetIR-style approach are candid about its real costs: it currently only reliably supports one PIP scope loaded at a time, has had stability issues ("PIP breaks after 30 seconds"), and is meaningfully more expensive to render than the native single-pass Ti view. Budget for that.

### 4.3 CBA_A3's "Scripted Optics" framework
The community's general-purpose infrastructure for PIP optics (used by several mods) formalizes the pattern above: a normal 2D/3D optic and a "PIP variant" using a special optics model with a render-to-target texture are defined as a pair, and the game swaps between them automatically based on the player's "Use picture-in-picture optics" setting, remaining save/load and Arsenal compatible. Worth adopting this framework rather than re-deriving the swap-item plumbing from scratch.

### 4.4 External post-processing injectors (ReShade / ENB) — a genuinely different lever
Because these hook the DirectX presentation layer *outside* the Arma engine entirely, they operate on the fully composited final frame — after Arma has already drawn native Ti, NVG, or anything else. This means:
- They are **not subject to the "ppEffects don't apply in Ti" restriction at all**, because they don't go through Arma's `ppEffect` API — they process the swapchain image directly. You could, in principle, get grain/scanlines/chromatic aberration/bloom/sharpening on top of vanilla native thermal for free this way.
- **Trade-offs that make this unsuitable as your primary architecture**, though useful as a personal/showcase layer: it's a separate client-side install the end user must opt into themselves (can't be bundled/enforced via your mod's PBO for consistent multiplayer visuals); it applies to the whole screen rather than being scoped to just a scope/goggle overlay (mitigable with ReShade's depth-buffer-aware add-ons, but adds complexity); and BattlEye/aggressive third-party anti-cheat (community reports specifically flag "Infistar"-style server admin tools) can flag or outright block DLL-injection-based tools, with inconsistent per-version, per-server results reported over the mod's history. Treat this as an optional "for screenshots/personal use" layer, not a shippable feature.

### 4.5 Where the engine is headed next (context, not something you can use today)
Bohemia's newer Enfusion engine (Arma Reforger, and the base for Arma 4) is visibly moving toward a more configurable, material-driven thermal pipeline than RV4's fixed renderer — RHS's Reforger port documentation references a "2D sight component V3 providing thermal vision support" and a scriptable `BaseWorld.SetCameraPostProcessEffect` thermal-tuning framework, explicitly **not** available in Arma 3. Useful to know so your team doesn't spend time hunting for an RV4 equivalent that was never shipped — this is a genuine RV4 architecture ceiling, not a documentation gap.

---

## 5. Recommended architecture (synthesis)

Split the problem by whether the target supports a PIP-capable render surface or not — the two tracks need genuinely different techniques.

**Track A — weapon scopes, vehicle sights, UAV/targeting-pod feeds (anything that can host a PIP camera):**
Use the SkeetIR/REAPIR pattern (§4.2) with `setPiPEffect [2]` as your base layer so you inherit real per-object heat data (correct foliage/camo penetration, real thermal crossover behavior if you drive it from §2.3's levers), then apply your own stylization to that texture: match real sensor grain to a target NETD "feel" rather than generic noise, blur to a plausible native-resolution ceiling before any upscale sharpening, bloom hot pixels outward instead of hard-clipping them, and offer real white-hot/black-hot/colorized palette toggles the way actual sights do. This gets you both true heat-based visibility *and* full post-process freedom simultaneously, because the stylization step happens on an ordinary texture outside the gated Ti pass — the same reason NVG modding already worked for you.

**Track B — the player's own primary view / helmet-worn devices (no PIP surface available):**
This is the harder case, and it's exactly where your "use NVG as the base view" instinct is correct — it's also how real ENVG-B fusion goggles are actually built (§1.3). Run the camera in `Normal` or `NVG` visionMode so you keep the full moddable `ppEffect` pipeline (with `ppEffectForceInNVG` to guarantee persistence), and source your "heat" information from the scriptable levers in §2.3 and the material-swap techniques in §4.1 rather than from the native Ti buffer, which isn't reachable from the main view without a PIP camera anyway. You won't get true per-pixel heat data this way (accept that — see §2.5's capability ceiling), but you gain complete stylistic control and — importantly — this is the same trade-off real fusion-goggle engineers made: two independently-sourced images, deliberately composited, rather than one "true" unified sensor.

**Either track:**
- Stop trying to `ppEffectCreate` your way into the native Ti pass. That's a confirmed dead end (§3), not a bug to keep debugging.
- Use `NoTiWrite` plus a proper glass RVMAT (or a dedicated cold/reflective StageTI value) so windows correctly block thermal, matching §1.1's physics and Arma's own known glass-related thermal fixes in past patches.
- Treat terrain/vegetation/rock dynamic heat as out of scope beyond the second-sun approximation (§2.5) — that's an engine ceiling every existing mod hits identically, not something a cleverer RVMAT will solve.
- If you want a "cheat" showcase/screenshot mode with zero engine restrictions, an optional ReShade profile (§4.4) is a legitimate but strictly client-side, opt-in extra — don't build core functionality on it.

---

## 6. Quick-reference tables

### Real vs. Arma-native-thermal behavior checklist
| Real-world physical behavior | Arma native Ti support? | How to add it |
|---|---|---|
| Blocked by ordinary glass | Not by default | `NoTiWrite` render flag + glass RVMAT |
| Thermal crossover at matched temps | Not modeled | Drive `setVehicleTIPars`/material swaps from a temperature model that can equalize target vs. background |
| Blooming around hot points | Partial (native LUTs have some falloff) | Add bloom/blur in your post-texture step (Track A) |
| Low native resolution / soft detail | Not modeled (native Ti is crisp) | Downsample-then-upsample or blur pass in your post-texture step |
| Sensor grain / NETD noise | Not modeled | Procedural noise layer, tuned to a target "sensitivity" feel, in your post-texture step |
| Reflective metals read cool/mirror-like | Partially, via material specular settings | Author StageTI ambient/specular per material rather than a single flat value |
| Engine/exhaust heat persists after shutdown, ramps up after start | Not automatic | Time-based model driving `setVehicleTIPars`, matching real thermal-inertia behavior |

### Engine commands at a glance
| Command | Scope | One-line purpose |
|---|---|---|
| `setTIParameter` | Global | Compress/offset the thermal display window (gain-like, not true contrast stretch) |
| `getTIParameters` | Global | Enumerate valid `setTIParameter` names |
| `setVehicleTIPars [e,w,g]` | Per-vehicle | Fake engine/wheel/weapon heat 0..1, infantry weapons excluded |
| `getVehicleTIPars` | Per-vehicle | Read-back |
| `setCamUseTI modeIndex` | Per-camera | Pick 1 of 8 baked palette LUTs for a scripted camera |
| `setPiPEffect [mode,...]` | Per-RTT-surface | 0 normal / 1 NVG / 2 native thermal / **3 custom color-correction** / 7–70 alt palettes |
| `disableTIEquipment` | Mission-wide | Hard-disable TI gear |
| `ppEffectForceInNVG` | Per-ppEffect | Keep a standard post effect alive while in NVG (no Ti equivalent exists) |

---

## 7. Sources

- Bohemia Interactive Community Wiki: [RVMAT basics](https://community.bistudio.com/wiki/RVMAT) · [setTIParameter](https://community.bistudio.com/wiki/setTIParameter) · [setVehicleTIPars](https://community.bistudio.com/wiki/setVehicleTiPars) · [setCamUseTI](https://community.bistudio.com/wiki/setCamUseTI) · [setPiPEffect](https://community.bistudio.com/wiki/setPiPEffect) · [Post Process Effects](https://community.bistudio.com/wiki/Post_Process_Effects) · [Weapon Config Guidelines](https://community.bistudio.com/wiki/Arma_3:_Weapon_Config_Guidelines) · [Sensors Config Reference](https://community.bistudio.com/wiki/Arma_3_Sensors_config_reference)
- Bohemia Interactive Forums: [RVMAT files / StageTI examples](https://forums.bohemia.net/forums/topic/231318-rvmat-files/) · [Thermal Signature Question](https://forums.bohemia.net/forums/topic/223414-thermal-signature-question/) · [Adding a ppEffect to Thermal Imaging (confirms ppEffects don't apply in Ti)](https://forums.bohemia.net/forums/topic/202982-adding-wetdistortion-ppeffect-to-thermal-imaging/) · [Picture in Picture enhancement request](https://forums.bohemia.net/forums/topic/206615-picture-in-picture/)
- A3TI (Arma 3 Thermal Improvement): [Steam Workshop page + changelog](https://steamcommunity.com/sharedfiles/filedetails/?id=2041057379)
- SkeetIR Thermal Weapon Sight: [Steam Workshop changelog](https://steamcommunity.com/sharedfiles/filedetails/changelog/2857096620)
- CBA_A3 [Scripted Optics documentation](https://github.com/CBATeam/CBA_A3/wiki/Scripted-Optics)
- KillzoneKid: [UAV, r2t and PiP scripting tutorial](https://killzonekid.com/arma-scripting-tutorials-uav-r2t-and-pip/)
- RHS Status Quo (Arma Reforger) documentation: [IR/NV/thermal status](https://docs.rhsmods.org/rhs-status-quo-user-documentation/arma-reforger/rhs-status-quo/general-systems/rhs-ir-and-nv)
- Thermal imaging physics: [FLIR/Infinity Optics explainer](https://www.infinitioptics.com/technology/thermal-imaging) · [IEEE TechNav infrared imaging overview](https://technav.ieee.org/area/infrared-imaging/) · [DSIAC white-hot/black-hot polarity research](https://dsiac.dtic.mil/tag/white-hot-wh-polarity) · [Thermal crossover, PMC review](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC5298629/) · [Glass blocks IR physics demo, UT Austin](https://lecturedemos.ph.utexas.edu/demo/158)
- Image intensifier physics: [Wikipedia — Image intensifier](https://en.wikipedia.org/wiki/Image_intensifier) · [Photonis/Exosens night vision technical overview](https://www.exosens.com/sites/default/files/2025-09/Photonis%20NV_One%20pager_16052025%20EN_VD.pdf)
- Fusion goggles: [L3Harris ENVG-B](https://www.l3harris.com/all-capabilities/enhanced-night-vision-goggle-binocular-envg-b) · [AN/PSQ-20B product specification](https://willsoptics.com/?p=2186)
- ReShade/BattlEye compatibility discussion: [ReShade forums](https://reshade.me/forum/troubleshooting/6420-reshade-blocked-by-battleye) · [Steam community discussion](https://steamcommunity.com/app/107410/discussions/0/1489992713711808045/)

---

*Compiled from public documentation, community forums, and vendor technical material as of September 2026. Engine command syntax should be re-verified against the current Bohemia wiki revision before implementation, since RV4 scripting commands do occasionally change parameters between game updates.*
