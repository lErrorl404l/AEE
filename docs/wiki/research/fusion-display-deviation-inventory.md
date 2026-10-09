# Fusion / NVG Display Deviation Inventory

Read-only audit of our fusion and NVG display code beside the four reference mods.

- Repo: `/ext/Development/AEE`, HEAD `286fbdd`.
- Behaviour of ours is cited as `addons/...` relative to the repo root.
- Theirs is cited by mod tree and line.
- Method: read every display/overlay function and config control in the four
  mods; map each to our counterpart; state the exact deviation, or mark
  MISSING, PARTIAL, REPLACED or UNKNOWN. No code was changed.

## Source trees

| Tag | Workshop | Tree | Identity |
|---|---|---|---|
| A | `3811605241` | `/tmp/opencode/ecoti/a/whale_ecoti_llll` | newest whale_ecoti. Capsule-topology silhouette, canvas, grid calibration. |
| W4 | `3810296503` | `/tmp/opencode/w4/whale_ecoti_llll` | whale_ecoti with drawn HUD, `fn_thermalFill`; silhouette by `drawLine3D`. |
| W3 | `3809860654` | `/tmp/opencode/w3/whale_ecoti_lll` | earliest whale_ecoti. Glass only, `fn_thermalFill` v1, `drawLine3D` outline. |
| B | `3759527903` | `/tmp/opencode/ecoti/b/FPANO_ECOTI` | distinct mod. Text HUD, map markers, rangefinder, HUD editor, radio bridge. |

Legend: COPIED = behaviour ported near-identically. REPLACED = same role, our
data or mechanism. PARTIAL = subset shipped. MISSING = no counterpart. EXTRA =
ours only, no source counterpart.

---

## 1. Mod A (`3811605241 whale_ecoti_llll`)

### 1.1 `functions/fn_showBox.sqf` (lines 1-31)

- Theirs: raise via `cutRsc ["whale_ecoti_llll_overlay", "PLAIN DOWN"]`
  (`fn_showBox.sqf:15`); hide by wiping every control background/text
  (`fn_showBox.sqf:19-27`) then `cutText` (`fn_showBox.sqf:30`).
- Ours: `addons/thermal_display/functions/hud/fnc_hudTapeBuild.sqf:28-56` (raise
  `cutRsc` at `:30`; clear at `:40-51`; `allControls` wipe at `:44-49`;
  `cutText` at `:51`).
- Status: PARTIAL. COPIED raise/clear/wipes.
- Deviation: the source re-cuts on every show to refresh a live glass size
  (`fn_showBox.sqf:14`); ours cuts once per session and clears the tape cache
  instead (`fnc_hudTapeBuild.sqf:32-35`). The glass is gone, so there is no
  size to refresh. The source's `whale_ecoti_llll_hudCache` reset
  (`fn_showBox.sqf:17,28`) maps to ours `QGVAR(hudTapeCache)`.

### 1.2 `functions/fn_boxOnLoad.sqf` (lines 1-40)

- Theirs: on `cutRsc` onLoad, store the display (`fn_boxOnLoad.sqf:24`) and
  position the glass control `910001` to a centred square of
  `_frac * safeZoneH` (`fn_boxOnLoad.sqf:27-31`), then colour it with
  `whale_ecoti_llll_tintColor`, default `[0.55,0.08,0.05,0.30]`
  (`fn_boxOnLoad.sqf:34,37-40`).
- Ours: the display onLoad stores the handle in RscTitles
  (`addons/thermal_display/RscTitles.hpp:138`) and there is no glass control.
- Status: MISSING. No counterpart; the glass is deleted outright.
- Deviation: our commit `286fbdd` removed the `whale_ecoti` glass (`idc 910001`)
  and its driver `fnc_hudTapeOnLoad.sqf`, because a translucent red-orange panel
  tinted the whole NVG image (operator report 2026-10-03). Our RscTitles
  `GVAR(fusionHud)` has no control `910001`; the compass tape and readouts
  remain (`RscTitles.hpp:145-292`). Our fusion HUD never sets a background on
  any control. Convenience alternative to their onLoad repositioning: our box
  geometry is a fixed macro `FUSION_HUD_BOX_FRACTION 0.40`
  (`addons/thermal/script_component.hpp:18`).

### 1.3 `functions/fn_collectHot.sqf` (lines 1-52)

- Theirs: `nearEntities ["CAManBase", _radius]` only, humans and animals
  (`fn_collectHot.sqf:29`); `_radius` default 2000 (`:11`), `_maxN` 60 (`:12`),
  optional ignore-friendlies (`:13,24-25`); distance sort (`:44`); cap (`:48`).
- Ours: `addons/thermal_display/functions/outline/fnc_outlineCollect.sqf`. Search set
  is `["CAManBase","Car","Tank","StaticWeapon","Air","Animal"]`
  (`fnc_outlineCollect.sqf:43`), default range 300 (`:22`); a target is hot
  when the maximum selection temperature exceeds ambient by 3 C (`:24,81`).
- Status: REPLACED. The list is driven by our physics state
  (`QGVAR(selTemperature)` against `aee_core_currentTemperature`), not by class
  membership. Per-object verdict cached 0.25 s in a HashMap (`:35-41,60-64`).
- Deviation: our collector keeps vehicles and static weapons; mod A removed
  them and keeps humans only (`fn_collectHot.sqf:29,32-34`). Our range default
  is 300 m, theirs 2000 m. Our key is `str _obj` because Arma HashMaps reject
  Object keys (`fnc_outlineCollect.sqf:52-58`), fixed in `2e4d012`. Our cap is
  applied by the outline drawer, not here; theirs caps at 60 here
  (`fn_collectHot.sqf:48`).

### 1.4 `functions/fn_convexHull.sqf` (lines 1-73)

- Theirs: screen-space convex hull by Andrew monotone chain
  (`fn_convexHull.sqf:29-73`).
- Ours: MISSING. The earlier hull of the projected skeleton was removed; the
  capsule-union topology replaces it (`addons/thermal_display/functions/outline/fnc_outlineDraw.sqf:8-11`).
- Status: MISSING. No counterpart file.
- Deviation: intentional. Their file is dead weight in the newest mod; the
  capsule union is the live mechanism in both.

### 1.5 `functions/fn_drawOutlines.sqf` (lines 1-626)

- Theirs: per-frame silhouette. Four LOD tables (`:159-224`), gear-adjusted
  capsule radii (`:348-369`), backpack inflation (`:374-376`), sensor blur
  `_infl = (_mpp*0.5) min 0.12` (`:298`) applied as `_r + _infl` (`:466`),
  topology pre-pass budget (`:229-248`), per-target topo cache `topo28`
  (`:419-477`), glow halo behind `_glowOn` (`:54,549`), clip to box
  (`:565-606`), canvas output (`:620-622`).
- Ours: `addons/thermal_display/functions/outline/fnc_outlineDraw.sqf` (worker),
  `fnc_outlineTopo.sqf` (topology), `fnc_outlineSkeleton.sqf` (LOD table),
  `fnc_outlineSensorLod.sqf` (sensor LOD), `fnc_outlineCanvas.sqf` (draw).
- Status: PARTIAL. Topology, sensor LOD, occlusion, canvas are COPIED. Several
  source passes are not ported.

Specific deviations:

| Item | Theirs | Ours | Status |
|---|---|---|---|
| Gear radius (headgear/vest/backpack) | `fn_drawOutlines.sqf:348-369` reads `gear32`, `gearMap`, scales capsule radii | Not ported; header says so (`fnc_outlineDraw.sqf:23-27`), radii are the unequipped table (`fnc_outlineSkeleton.sqf:26-83`) | MISSING |
| Backpack inflation | `fn_drawOutlines.sqf:374-397` inflates the two virtual points | Points used as-is; capsule stays hidden in the torso (`fnc_outlineDraw.sqf:171-184`) | MISSING |
| Sensor blur `_infl` | Defined `:298`, applied `_r+_infl` at `:466` | No `_infl`; only `[_hSens] call FUNC(outlineSensorLod)` (`fnc_outlineDraw.sqf:155-157`, `fnc_outlineSensorLod.sqf:18-23`) | MISSING |
| Topology budget / pre-pass | `:229-248`, `_budget` from setting 2 (`fn_preInit.sqf:67`) | None; topology recomputed every frame for every hot target (`fnc_outlineDraw.sqf:219`) | MISSING |
| Per-target topo cache `topo28` | `:419-477`, interval from setting 0.10 s (`fn_preInit.sqf:68`) | None | MISSING |
| Glow halo | Only when `_glowOn` (default false) and `_h1080 > _softMin` (`:54,549`) | Always draws the soft underlay when `_h1080 > 160` (`fnc_outlineDraw.sqf:280`) | REPLACED |
| Brightness / whiteness | Settings `brightness` 1.30, `whiteness` 0 (`fn_preInit.sqf:144-150,254-260`) | Hardcoded, no colour whitening: `_col = [1.00,0.41,0.10]`, `_opac = 0.55` (`fnc_outlineDraw.sqf:54-55`) | REPLACED |
| Opacity / line width | Settings `opacity` 0.55, `lineWidth` 2 (`fn_preInit.sqf:176-182,246-252`) | Hardcoded `_opac`/`_wCore` (`fnc_outlineDraw.sqf:55-56`) | REPLACED |
| Far width | Setting `farWidth` 0.60 (`fn_preInit.sqf:238-244`) | Hardcoded `((sqrt(_h1080/120)) max 0.60) min 1` (`fnc_outlineDraw.sqf:272`) | REPLACED |
| Max outlines | Setting `maxOutlines` (`fn_preInit.sqf:184-196`) | None; `_drawn` counted but not capped (`fnc_outlineDraw.sqf:123,337`) | MISSING |
| Ray budget / visibility interval | Settings `rayBudget` 12, `visInterval` 0.25 (`fn_preInit.sqf:74-77`); cached per zone | Inline `checkVisibility`/`lineIntersectsSurfaces` each pass, no budget, no cache (`fnc_outlineDraw.sqf:224-240`) | MISSING |
| Occlusion toggle | Setting `occlusion` (`fn_preInit.sqf:262-268`) | Always on | MISSING |
| Clip to box | Setting `clipToBox` true (`fn_preInit.sqf:70`); branches on `_clip` (`:565`) | Always clips when not `_fullIn` (`fnc_outlineDraw.sqf:289-335`) | REPLACED |
| Colour source | `outlineColor [1.00,0.41,0.10,1.00]` (`fn_preInit.sqf:50`) | Hardcoded RGB `[1.00,0.41,0.10]`, alpha from `_opac` (`fnc_outlineDraw.sqf:54-55,116`) | COPIED value, REPLACED wiring |
| Sensor resolution | Setting `sensorRes` default 240 (`fn_preInit.sqf:217-227`) | Hardcoded `_sensRes = 240` (`fnc_outlineDraw.sqf:58`) | COPIED value, REPLACED wiring |
| Range / fade | Setting `range` default 400, fade last quarter (`fn_preInit.sqf:136-142`; `fn_drawOutlines.sqf:289`) | Hardcoded `_range = 400`, same fade (`fnc_outlineDraw.sqf:59,150`) | COPIED |
| HUD box fraction | `boxSize` 0.40 (`fn_preInit.sqf:39`), read as `_frac` 0.30 fallback (`fn_drawOutlines.sqf:40`) | Hardcoded `_frac = 0.30` (`fnc_outlineDraw.sqf:57`) | COPIED fallback |
| Field gate | Source uses only the HUD box | Extra gate `FUNC(fusionFovGate)` at the resolved thermal half-angle before the box test (`fnc_outlineDraw.sqf:131-132`) | EXTRA |
| Hot-list source | `whale_ecoti_llll_hot` from `fn_collectHot` | `[] call FUNC(outlineCollect)` (`fnc_outlineDraw.sqf:62`) | REPLACED |

LOD table: our `fnc_outlineSkeleton.sqf:26-83` matches mod A `fn_drawOutlines.sqf:159-224`
exactly except the blob level (LOD 3): mod A states three-element capsules
`[1,0,0.24,0]` (`fn_drawOutlines.sqf:219`), ours states five-element capsules
with explicit B radius `[1,0,0.24,0,0.24,2]` (`fnc_outlineSkeleton.sqf:78`). Same
geometry, explicit form.

### 1.6 `functions/fn_drawHUD.sqf` (lines 1-214)

- Theirs: compass tape. Heading from `positionCameraToWorld` (`fn_drawHUD.sqf:37-40`).
  Geometry hardcoded `_tapeFr 0.40`, `_span 60` (`:79-80`); scales from
  `_scl`/`_hudY` settings (`:48-49`); 13 labels `920011+` (`:145`), 25 ticks
  `920031+` (`:167`), 8 cardinals `920061+` (`:192`); colours from
  `rulerColor` default `[1.00,0.30,0.00,0.60]` (`:44`).
- Ours: `addons/thermal_display/functions/hud/fnc_hudTapeDraw.sqf`.
- Status: COPIED. Same geometry, idc layout, change cache. Heading comes from
  `EFUNC(core,getEyeState)` instead of the camera pair (`fnc_hudTapeDraw.sqf:34-42`).
- Deviation: our scale/span are compile-time macros `FUSION_HUD_SCALE 1.14`,
  `FUSION_HUD_TAPE_SPAN 60` (`addons/thermal/script_component.hpp:20-21`), not
  settings; the source exposes them through `fn_preInit.sqf:52,79-80`. Our ruler
  colour is the same value as a macro (`script_component.hpp:27`); source
  `rulerColor` at `fn_preInit.sqf:56`. Our tape loses the glass brightness
  channel: the source multiplies by a `bootProfile` whose index 0 is bagged from
  the glass (`fn_drawHUD.sqf:57-59`); ours reads `hudK` only
  (`fnc_hudTapeDraw.sqf:48-58`).

### 1.7 `functions/fn_drawInfo.sqf` (lines 1-124)

- Theirs: top-left grid/position `920102`, top-right time `920101`. Position is
  an invented latitude/longitude from the map config via `fn_gridCal`
  (`fn_drawInfo.sqf:61-88`). Time from `daytime` (`:106`).
- Ours: `addons/thermal_display/functions/hud/fnc_hudTapeInfo.sqf`. Left control
  `920102` prints `mapGridPosition` plus ASL height (`fnc_hudTapeInfo.sqf:56-64`).
- Status: PARTIAL. Layout COPIED; the position source is REPLACED.
- Deviation: no `fn_gridCal`; we print the engine grid string directly
  (`fnc_hudTapeInfo.sqf:60`). Their time format `HHMM` from `daytime`
  (`fn_drawInfo.sqf:106-117`); ours also `HHMM` (`fnc_hudTapeInfo.sqf:90-99`).
  We add an environment line on a third control `920103`
  (`fnc_hudTapeInfo.sqf:68-83`; control declared `RscTitles.hpp:173-181`), which
  the source does not have. The source's corner show/hide settings `Show Time`,
  `Show Coordinates` (`fn_preInit.sqf:152-166`) have no counterpart; our corners
  are always shown while the tape is up.

### 1.8 `functions/fn_boot.sqf` (lines 1-124)

- Theirs: power-on 1.05 s, power-off 0.70 s (`fn_boot.sqf:54,78`); two flashes
  at 0.10 s and 0.40 s (`:50`); glass, HUD and info brightness
  (`:60-73,84-93`); writes `bootProfile` (3 channels, `:99`) and refreshes the
  glass (`:110-123`).
- Ours: `addons/thermal_display/functions/hud/fnc_hudTapeBoot.sqf`.
- Status: PARTIAL. COPIED envelope: same durations
  (`FUSION_HUD_BOOT_ON 1.05`, `FUSION_HUD_BOOT_OFF 0.70`,
  `script_component.hpp:23-24`), same 0.10/0.40 flashes with exponent 0.55
  (`fnc_hudTapeBoot.sqf:59-66`), same on-fade ranges (`:74-79`) and off-fade
  (`:87-93`).
- Deviation: the source publishes a three-channel profile
  `[HUD, reserved, small UI]` (`fn_boot.sqf:99,26`) and also drives the glass
  (`:33-34,109-123`). Ours publishes two channels `[hudK, infoK]`
  (`fnc_hudTapeBoot.sqf:98`) because the glass is removed. Our driver owns the
  display lifetime (`:33-45,100-106`); the source's `fn_boot` also toggles the
  box (`fn_boot.sqf:102-107`).

### 1.9 `functions/fn_outlineMap.sqf` (lines 1-64)

- Theirs: full-screen transparent `RscMapControl`, idc `930001`, placed in a
  corner at max zoom, hidden two frames, draw handler over
  `whale_ecoti_llll_mapSegs` (`fn_outlineMap.sqf:31-63`).
- Ours: `addons/thermal_display/functions/outline/fnc_outlineCanvas.sqf`. Same
  mechanism; idc `1301` (`fnc_outlineCanvas.sqf:37`), segs `QGVAR(outlineSegs)`
  (`:30,49`), same two-frame hide and calibration (`:42-72`).
- Status: COPIED.
- Deviation: control idc and namespace keys differ; ours returns the map
  control as the calibration's fifth element (`fnc_outlineCanvas.sqf:72`) and
  the drawer uses it (`fnc_outlineDraw.sqf:49,293`). The source added the
  control to its return only in v34 (`fn_outlineMap.sqf:64`). No behaviour
  change. Our display `GVAR(fusionOutline)` idc `10780` (`RscTitles.hpp:22-23`)
  versus the source overlay idc `-1` (`config.cpp:74`).

### 1.10 `functions/fn_outlineTopo.sqf` (lines 1-255)

- Theirs: capsule-union topology, `[t,c,s]` polylines, adaptive sampling
  (`fn_outlineTopo.sqf:102-104`), bisection crossings (`:178-205`), straight-side
  merge (`:212-231`), Chaikin smoothing (`:233-250`).
- Ours: `addons/thermal_display/functions/outline/fnc_outlineTopo.sqf`.
- Status: COPIED. Same algorithm and same sampling bounds `_m` 3..6, `_k` 1..4
  (`fnc_outlineTopo.sqf:124-125`; source `:103-104`), same merge and smoothing.
- Deviation: ours reads capsule fields with `select` plus a count guard so the
  pure kernel runs in the test harness (`fnc_outlineTopo.sqf:20-23,54-62,105-108`);
  the source uses `params` (`fn_outlineTopo.sqf:41`). No numeric change.

### 1.11 `functions/fn_gridCal.sqf` (lines 1-104)

- Theirs: calibrate the Arma map grid once per world by bisection against
  `mapGridPosition`; cache `whale_ecoti_llll_gridCal` (`fn_gridCal.sqf:23-24,101-104`);
  return `[world, true, n, [size,origin,sign]X, [size,origin,sign]Y]`.
- Ours: MISSING. No file. Our HUD prints `mapGridPosition` unchanged
  (`fnc_hudTapeInfo.sqf:60`).
- Status: MISSING.
- Deviation: our grid is the raw engine string, so we lose `fn_gridCal`'s
  precision control (their `gridDigits` setting 6/8/10-digit,
  `fn_preInit.sqf:229-236`; applied `fn_drawInfo.sqf:70-85`). The value is the
  same source, with less formatting.

### 1.12 `functions/fn_isThermalNVG.sqf` (lines 1-70)

- Theirs: decide whether a unit's HMD may run ECOTI. Whitelist with prefix
  wildcard (`fn_isThermalNVG.sqf:31-49`); else require both NVG and TI in
  `visionMode`/`thermalMode` (`:52-70`); `requireThermal` option (`:27`).
- Ours: capability is resolved from the device corpus by
  `FUNC(resolveFusionDevice)` and `FUNC(isFusionCapable)`, invoked in the
  optics vision dispatch (`addons/optics/XEH_postInit.sqf:109-117`).
- Status: REPLACED.
- Deviation: no class-name whitelist and no `visionMode` heuristic; a device is
  fusion-capable when our data says it is. The source's fuzzy name matching is
  deliberately not adopted (recorded in project memory, A3TI audit item 5).

### 1.13 `functions/fn_preInit.sqf` (lines 1-316)

- Theirs: writes locked parameters and settings. Box size 0.40 (`:39`); glass
  tint `[0.64,0.31,0.18,0.15]` (`:49`); outline colour `[1.00,0.41,0.10,1.00]`
  (`:50`); ruler/info colour `[1.00,0.30,0.00,0.60]` (`:56-57`); HUD scale 1.14
  (`:52`); topo budget 2 / interval 0.10 (`:67-68`); ray budget 12 / vis
  interval 0.25 (`:76-77`); soft min 160 px (`:79`). Settings for brightness,
  range, detail range, line width, max outlines, glow, sensor resolution, grid
  digits, far width, opacity, whiteness, occlusion (`:114-268`). Keybinds V
  (`:287-294`) and Shift+B (`:299-314`).
- Ours: compile-time macros in `addons/thermal/script_component.hpp`
  (`FUSION_HUD_BOX_FRACTION 0.40`, `FUSION_HUD_SCALE 1.14`,
  `FUSION_HUD_RULER_COLOR`, `FUSION_HUD_INFO_COLOR`, `FUSION_FRAME_MIN_INSET`;
  lines 10-28) and CBA settings in `addons/thermal/initSettings.inc.sqf`.
- Status: PARTIAL. Kept as settings: `fusionAlwaysOn` (`:23`), `fusionFovFrame`
  (`:30`), `fusionOutline` (`:36`), `fusionSolidFill` (`:45`), `fusionHud`
  (`:55`).
- Deviation (largest): almost every display tuning value is now a fixed
  constant, not an operator setting. Theirs exposes brightness, opacity,
  whiteness, line width, far width, max outlines, glow, sensor resolution,
  detail range, range, occlusion, ray budget, visibility interval, topo budget,
  topo interval, grid precision, HUD scale/Y, and the per-corner show toggles.
  Ours exposes none of those; they are hardcoded in `fnc_outlineDraw.sqf` and
  `script_component.hpp`. The glass tint colour is entirely gone.

### 1.14 `functions/fn_postInit.sqf` (lines 1-111)

- Theirs: two mission `Draw3D` handlers. One runs `fn_drawOutlines` with an
  optional profile block (`fn_postInit.sqf:20-43`); the other runs
  `fn_boot`, `fn_drawHUD`, `fn_drawInfo` (`:45-49`). A 0.10 s loop refreshes the
  hot list, auto-closes on NVG off, and re-cuts the box on colour/size change
  (`:51-106`).
- Ours: `addons/thermal/XEH_postInit.sqf:15-32`. One `Draw3D` handler calls
  `FUNC(outlineDraw)`, `FUNC(hudTapeBoot)`, `FUNC(hudTapeDraw)`; a 0.1 s PFH
  runs `FUNC(hudTapeInfo)` (`:29`).
- Status: PARTIAL. COPIED wiring. The source separates the outline handler from
  the HUD handler so one fault does not blank the other
  (`fn_postInit.sqf:16-18`); ours also gives the outline its own display and
  handler. The source's hot-list refresh and box re-cut loop are not ported:
  our hot list refreshes inside `outlineCollect` (0.25 s cache) and the box
  geometry is fixed.
- Deviation: no profiler block (`fn_postInit.sqf:24-39`); no auto-start / NVG
  edge logic here (ours lives in the optics dispatch).

### 1.15 `functions/fn_toggle.sqf` (lines 1-47)

- Theirs: V key. `isThermalNVG` and `currentVisionMode in [1,2]` gate; blocks
  while the Zeus display 312 is open (`fn_toggle.sqf:36-40`); sets `_on`, shows
  the box, starts the power-on animation (`:42-46`); on off, starts power-off
  and lets `fn_boot` finish it (`:28-33`).
- Ours: split. `FUNC(outlineToggle)` raises/clears only the canvas
  (`addons/thermal_display/functions/outline/fnc_outlineToggle.sqf:23-36`); the
  fusion on/off gate and animation live in the optics dispatch and
  `FUNC(hudTapeBoot)` (`addons/optics/XEH_postInit.sqf:109-121`,
  `fnc_hudTapeBoot.sqf:33-45`).
- Status: REPLACED (decomposed).
- Deviation: no V-key toggle in thermal; fusion is entered through the optics
  vision dispatch. The source's Zeus-display guard and NVG-on guard are not in
  our thermal toggle; capability gating is `isFusionCapable`
  (`addons/optics/XEH_postInit.sqf:109`).

### 1.16 `config.cpp` controls (lines 1-220)

- Theirs: `RscTitles \ whale_ecoti_llll_overlay`, idd `-1`, duration `1e10`
  (`:72-75`), onLoad calls `fn_boxOnLoad` (`:78`). Controls: glass `ecoti_tint`
  idc `910001` (`:83-93`); `hud_pos` `920102` (`:111`); `hud_time` `920101`
  (`:112`); `hud_head` `920001` (`:114`); `hud_mark` `920002` (`:115`); labels
  `920011-23` (`:117-129`); ticks `920031-55` (`:131-155`); cardinals
  `920061-68` (`:160-167`); canvas `ecoti_canvas` idc `930001` (`:177-217`).
  Font `EtelkaMonospaceProBold`; heading `sizeEx 0.009`, labels `0.006`.
- Ours: `addons/thermal_display/RscTitles.hpp`. `GVAR(fusionHud)` idd `10782`
  (`:133-134`); `GVAR(fusionOutline)` idd `10780` (`:22-23`); `GVAR(fusionFrame)`
  idd `10779` (`:80-81`). Tape controls keep the source idcs:
  heading `920001` (`:193-194`), mark `920002` (`:205-206`), labels
  `920011-23` (`:225-237`), ticks `920031-55` (`:248-272`), cardinals
  `920061-68` (`:285-292`), info `920102` (`:164-165`), clock `920101`
  (`:182-183`).
- Status: PARTIAL.
- Deviation: no glass control `910001`. We add `920103` environment line
  (`RscTitles.hpp:173-181`). The canvas is a separate display idc `1301`
  (`RscTitles.hpp:32-33`) versus the source's `930001` inside the same overlay
  (`config.cpp:179`). Duration `999999` (`:140`) versus `1e10` (`config.cpp:75`).
  Our local control bases avoid engine class names (`RscTitles.hpp:121-132`).
  `GVAR(fusionFrame)` is EXTRA: a four-bar thermal-channel frame with no source
  counterpart; it is discarded at the device edge (`FUSION_FRAME_MIN_INSET
  0.97`, `script_component.hpp:10`; `fnc_updateFusionFrame.sqf:43-49`).

### 1.17 Other Mod A files

`fn_outlineMap.sqf`, `fn_outlineTopo.sqf`, `fn_convexHull.sqf`,
`fn_gridCal.sqf`, `fn_isThermalNVG.sqf`, `fn_preInit.sqf`, `fn_postInit.sqf`
are covered above. Mod A has no `fn_thermalFill.sqf`: full thermal fill was
removed at v30 (`fn_drawOutlines.sqf:18-20`; `fn_postInit.sqf:19`).

---

## 2. Mod W4 (`3810296503 whale_ecoti_llll`)

Mod W4 is the direct source of our compass tape and our solid fill. Its
silhouette uses `drawLine3D` world lines, not a canvas
(`/tmp/opencode/w4/whale_ecoti_llll/functions/fn_drawOutlines.sqf:26-27,148-157`).
It has no `fn_outlineMap`, `fn_outlineTopo`, `fn_convexHull` or `fn_gridCal`.

### 2.1 `functions/fn_thermalFill.sqf` (lines 1-130)

- Theirs: save each texture slot, paint one solid colour, restore on leave. The
  live list is `whale_ecoti_llll_hotVisible`, produced by `fn_drawOutlines`
  (`fn_thermalFill.sqf:42-45,127`). Colour from `outlineColor`, default
  `[1.00,0.41,0.10,1.00]` (`:48`); texture
  `#(rgb,8,8,3)color(r,g,b,1.0)` (`:49`). Per-pass signature cache
  (`:58-60`). Slot count is the larger of live textures and config defaults,
  `12` for a man and `8` otherwise (`:107-123`). Restore drops empty saved
  strings (`:92`).
- Ours: `addons/thermal_display/functions/fusion/fnc_applyFusionFill.sqf`.
- Status: COPIED mechanism, REPLACED driving data.
- Deviation: our live list is `FUNC(outlineCollect)` filtered by
  `FUNC(fusionFovGate)` (`fnc_applyFusionFill.sqf:72,78-94`), not the source's
  `hotVisible`. Our colour is hardcoded `[1.00,0.41,0.10]`
  (`fnc_applyFusionFill.sqf:98`), not read from a setting. Our slot fallback is
  `[8,12] select isKindOf "CAManBase"` (`:173`) versus the source's if/else
  (`fn_thermalFill.sqf:113`), same values. Our restore and EXIT path are ported
  (`:45-60,142-159`); ours logs at 30 s intervals (`:101-108`) whereas the
  source logs nothing.

### 2.2 `functions/fn_drawHUD.sqf`, `fn_drawInfo.sqf`, `fn_boot.sqf`, `fn_showBox.sqf`, `fn_boxOnLoad.sqf`, `fn_preInit.sqf`

- These are the immediate source of our tape, info, boot, build and constants.
  Ours is described in section 1; the mapping is:
  - `fn_drawHUD.sqf` -> `fnc_hudTapeDraw.sqf` (COPIED).
  - `fn_drawInfo.sqf` -> `fnc_hudTapeInfo.sqf` (PARTIAL; invented lat/lon
    replaced by `mapGridPosition`).
  - `fn_boot.sqf` -> `fnc_hudTapeBoot.sqf` (PARTIAL; glass channel removed).
  - `fn_showBox.sqf` -> `fnc_hudTapeBuild.sqf` (PARTIAL).
  - `fn_boxOnLoad.sqf` -> RscTitles onLoad + no glass (MISSING).
  - `fn_preInit.sqf` -> macros + `initSettings.inc.sqf` (PARTIAL).
- W4 `config.cpp` (169 lines) declares the glass `910001`
  (`/tmp/opencode/w4/whale_ecoti_llll/config.cpp:82-92`) and the same HUD
  controls (`:109-166`) as Mod A, with no canvas. Our deviations are the same as
  section 1.16.

### 2.3 W4 `fn_drawOutlines.sqf` (lines 1-327)

- Theirs: `drawLine3D` world outlines, computes and publishes `hotVisible`
  (`fn_drawOutlines.sqf:35,327`).
- Ours: `fnc_outlineDraw.sqf` uses the canvas (no `drawLine3D`). The
  `hotVisible` list has no analogue; the fill uses `outlineCollect` plus
  `fusionFovGate`.
- Status: REPLACED (mechanism superseded by Mod A's canvas).
- Deviation: our outline mechanism follows Mod A (canvas + topology), not W4.

### 2.4 W4 `fn_collectHot.sqf`, `fn_convexHull.sqf`, `fn_isThermalNVG.sqf`, `fn_postInit.sqf`, `fn_preInit.sqf`, `fn_toggle.sqf`, `fn_showBox.sqf`, `fn_boxOnLoad.sqf`

Same roles as section 1, mapped to the same counterparts. `fn_convexHull.sqf`
is MISSING in ours (section 1.4).

---

## 3. Mod W3 (`3809860654 whale_ecoti_lll`)

Earliest tree. Glass only, no drawn HUD, silhouette by `drawLine3D`, fill v1.

### 3.1 `functions/fn_thermalFill.sqf` (lines 1-91)

- Theirs: paints `whale_ecoti_lll_hot` every pass with no field gate
  (`fn_thermalFill.sqf:22-23,88`); nested `O(n^2)` already-lit search
  (`:64-65`); no signature cache. Colour from `outlineColor`
  (`:26`).
- Ours: `fnc_applyFusionFill.sqf` is the W4 version (field-gated, cached,
  flattened list). See 2.1.
- Status: REPLACED. We ship the later W4 algorithm; the earlier one flickers
  and repaints outside the view (our header records this,
  `fnc_applyFusionFill.sqf:5-7`).

### 3.2 `functions/fn_drawOutlines.sqf` (lines 1-234)

- Theirs: `drawLine3D` skeleton outlines; models in simulation state
  (`/tmp/opencode/w3/whale_ecoti_lll/functions/fn_drawOutlines.sqf:11,26-27`),
  no `hotVisible`.
- Ours: none; our outline follows Mod A.
- Status: REPLACED.

### 3.3 `config.cpp` (lines 1-94)

- Theirs: `RscTitles \ whale_ecoti_lll_overlay` with only the glass control
  `910001` (`/tmp/opencode/w3/whale_ecoti_lll/config.cpp:79-89`); no HUD, no
  canvas.
- Ours: `fusionHud` (tape) plus `fusionOutline`/`fusionFrame`. No glass.
- Status: MISSING (glass), EXTRA (tape/canvas).
- Deviation: our glass removal matches the operator direction; the HUD and
  canvas came from later trees.

### 3.4 Other W3 functions

`fn_collectHot.sqf`, `fn_convexHull.sqf`, `fn_isThermalNVG.sqf`,
`fn_postInit.sqf`, `fn_preInit.sqf`, `fn_showBox.sqf`, `fn_boxOnLoad.sqf`,
`fn_toggle.sqf` are the same roles as section 1 and map to the same
counterparts. W3 has no `fn_drawHUD`, `fn_drawInfo` or `fn_boot`; those first
appear in W4.

---

## 4. Mod B (`3759527903 FPANO_ECOTI`)

Distinct mod. Text HUD, map markers, rangefinder, HUD editor, radio bridge,
CfgMarkers, sounds. Our port is `aee_optics`.

### 4.1 `ui_hud.hpp` (lines 1-145)

- Theirs: `RscText` base (`:1-10`); `RscTitles \ FPANO_ECOTI_HUD` idd `-1`
  (`:12-16`); controls with list (`:21-31`): cardinal `9010` (`:33-43`),
  degrees `9003` (`:45-55`), grid `9004` (`:57-67`), altitude `9005`
  (`:69-79`), time `9006` (`:81-91`), labels `9011`/`9007` (`:93-115`),
  temperature `9012` (`:117-127`), radio `9020` (`:129-143`). Fonts
  `PuristaMedium`, radio `EtelkaMonospacePro`; radio colour
  `[1.0,0.55,0.18,0.95]`.
- Ours: `addons/hud/RscTitles.hpp`. `GVAR(hud)` idd `10781` (`:14-15`),
  controls `9010` cardinal (`:44-53`), `9003` degrees (`:55-64`), `9004` grid
  (`:66-75`), `9005` altitude (`:77-85`), `9006` time (`:87-95`), labels
  `9011`/`9007` (`:97-117`), `9012` temperature (`:119-128`), plus EXTRA
  humidity `9013` (`:130-139`) and wind `9014` (`:141-150`).
- Status: PARTIAL. Layout COPIED.
- Deviation: we drop the radio control `9020` and its colour. We add two
  environment controls (`9013`, `9014`). Label text differs: ours reads
  `AEE ENV` / `HUD` (`:99,110`) versus `F-PANO` / `ECOTI` (`:95,107`). The
  source declares `shadow = 1` on the base (`:5`); ours sets it on the local
  base (`:31`).

### 4.2 `scripts/FPANO_fnc_hud.sqf` (lines 1-237)

- Theirs: 0.1 s loop; gates on `currentVisionMode == 1` and not `visibleMap`
  (`:23-29`); `cutRsc` on layer `7734` (`:33`); bearing from
  `positionCameraToWorld` (`:42-45`); cardinal sectors (`:51-61`); grid split
  (`:72-82`); temperature from `ambientTemperature` (`:84-89`); time via
  `BIS_fnc_timeToString` (`:185`); altitude from `getPosASL` (`:184`); per-
  control show toggles (`:162-179`); radio comms text (`:189-226`).
- Ours: `addons/hud/functions/hud/fnc_hudUpdate.sqf` (driver),
  `fnc_hudFormatHeading.sqf` (cardinal/degrees), `fnc_hudFormatGrid.sqf`
  (grid split), `fnc_hudFormatRange.sqf` (distance).
- Status: PARTIAL, REPLACED data.
- Deviation: bearing comes from `EFUNC(core,getEyeState)` forward vector
  (`fnc_hudUpdate.sqf:40-47`) instead of the camera pair. Grid formatting is
  COPIED (`fnc_hudFormatGrid.sqf:22-28`). Heading sectors COPIED
  (`fnc_hudFormatHeading.sqf:24-56`). Temperature COPIED role, source
  `ambientTemperature` replaced by `aee_core_currentTemperature`
  (`fnc_hudUpdate.sqf:53,70`); we add humidity and wind (`:54-56,71-72`). No
  radio line. The source's per-control visibility toggles map to our single
  `hudEnabled` setting (`addons/optics/initSettings.inc.sqf:65`) and do not
  support per-control hiding. The source's HUD editor drives its per-control
  positions (`:92-137`); ours has no editor, so positions are fixed.

### 4.3 `scripts/FPANO_fnc_mapMarkers.sqf` (lines 1-336)

- Theirs: 1 s cache loop for markers, ally names, friendly vehicles
  (`:127-236`); Draw3D worker with filter modes and icon/text scaling
  (`:239-336`); distances `MaxMarkerDist 2500`, `MaxVehicleDist 2000`,
  `MaxAirDist 3500`, `MaxUnitNameDist 120` (`:17-20`); raster icons
  (`:23-30`).
- Ours: `addons/hud/functions/hud/fnc_hudMarkers.sqf`.
- Status: PARTIAL.
- Deviation: we port the marker scan and 3D label only (`:30-42`); the ally
  name and friendly vehicle passes are omitted, as is the filter-mode system
  (`fnc_hudMarkers.sqf` header `:10-14`). We draw empty-icon 3D text, not the
  source raster icons. Our range is fixed 2500 m (`fnc_hudMarkers.sqf:49`); the
  source scales icon and text, which we do not (`FPANO_fnc_mapMarkers.sqf:241-246,290-330`).

### 4.4 `scripts/FPANO_fnc_rangefinder.sqf` (lines 1-40)

- Theirs: Draw3D reads a cached ping `FPANO_ECOTI_RangePing` set by a keybind
  (`:14-17`); draws the engine dot icon with distance
  (`:26-38`).
- Ours: `addons/hud/functions/hud/fnc_hudRangefinder.sqf`.
- Status: REPLACED.
- Deviation: our worker casts `lineIntersectsSurfaces` itself, throttled to
  0.5 s (`fnc_hudRangefinder.sqf:27-42`), instead of reading a keybind ping. We
  draw empty-icon 3D text (`:47-57`), so no raster asset is referenced.

### 4.5 `scripts/FPANO_fnc_editor.sqf` (lines 1-339)

- Theirs: in-game HUD position editor. Creates an input display, drags controls,
  saves positions to `profileNamespace` (`FPANO_fnc_editor.sqf:135,148-159,205-212`).
- Ours: MISSING. Deliberately skipped: unsafe in-game editor.
- Status: MISSING.

### 4.6 `scripts/FPANO_fnc_radioBridge.sqf` (lines 1-442)

- Theirs: ACRE2 and TFAR bridge. Local TX state, remote talkers, per-radio
  channel text, comms prompt (`FPANO_fnc_radioBridge.sqf:10-14,115-166,313-403,406-441`).
- Ours: MISSING. Deliberately skipped: aee owns radio.
- Status: MISSING.
- Deviation: no radio comms readout on our HUD (control `9020` also gone,
  section 4.1).

### 4.7 `config.cpp` (lines 1-55)

- Theirs: `CfgPatches` (`:1-8`); `Extended_PostInit_EventHandlers` calling
  `XEH_postInit.sqf` (`:10-14`); `CfgMarkerClasses \ FPANO_ECOTI_Markers`
  (`:16-20`); `CfgMarkers` with `FPANO_marker_POI`, `_OP`, `_FSS` (`:22-45`);
  `CfgSounds \ fpano_sound_toggle` (`:47-54`); `#include "ui_hud.hpp"` (`:56`).
- Ours: `addons/optics/config.cpp` declares `CfgPatches` and includes
  `RscTitles.hpp`; there is no `CfgMarkerClasses`, no `CfgMarkers`, no
  `CfgSounds`.
- Status: MISSING for CfgMarkers and CfgSounds. PARTIAL for PostInit (ours is
  `addons/optics/XEH_postInit.sqf:142-151`).

### 4.8 `CfgMarkers`

- Theirs: three custom marker types `FPANO_marker_POI/OP/FSS`, class
  `mil_dot`, `size 32`, icons `POI.paa`/`OP.paa`/`FSS.paa`
  (`/tmp/opencode/ecoti/b/FPANO_ECOTI/config.cpp:22-45`).
- Ours: MISSING. `fnc_hudMarkers.sqf` reads `allMapMarkers` and draws labels;
  it does not define marker types.
- Deviation: the three mod-specific marker types and their raster icons cannot
  be created. Our marker aid is read-only.

### 4.9 `XEH_postInit.sqf` (lines 1-304)

- Theirs: registers 13 CBA settings (`:6-168`), compiles the editor (`:171`),
  starts the HUD/marker/rangefinder/radio scripts (`:180-195`), and registers
  four keybinds: toggle overlay, rangefinder ping, cycle filter, edit HUD
  (`:198-302`).
- Ours: `addons/optics/XEH_postInit.sqf:142-151` starts `hudRangefinder`,
  `hudMarkers` and the `hudUpdate` PFH. Setting `hudEnabled` default false
  (`addons/optics/initSettings.inc.sqf:65`).
- Status: PARTIAL.
- Deviation: one setting instead of 13; no keybinds; no editor; no radio; no
  filter modes. The source starts its scripts from a mission spawn; ours starts
  them from module postInit behind `hasInterface`.

---

## 5. Cross-cutting deviations (ours only)

These have no counterpart in any of the four mods.

### 5.1 NVG phosphor colourise

- Source mods: no tube model. They leave the engine NVG green as-is and lay a
  red-orange glass over it (`/tmp/opencode/ecoti/a/whale_ecoti_llll/functions/fn_boxOnLoad.sqf:34,37-40`).
- Ours: `addons/nightvision/functions/fnc_applyNVGTubeModel.sqf` owns the tube
  output. The phosphor is a `ColorCorrections` colorize array (comment
  `:128-137`): P43 green `[1.3,1.2,0.0,0.9]` (`:153,212,224,276`), P45 white
  `[1.1,0.8,1.9,0.9]` (`:198,281`), P20 yellow-green `[1.4,1.3,0.0,0.9]`
  (`:233`); desaturation weights `[6,1,1,0]` green / `[1,1,6,0]` white. The
  device corpus overrides the tier (`:266-283`).
- Status: EXTRA.
- Deviation: our NVG base is a physical tube model; the source's glass tint was
  the wrong place to colour the image and we removed it (`286fbdd`).

### 5.2 Thermal-channel FOV frame

- Source: none.
- Ours: `GVAR(fusionFrame)` (`RscTitles.hpp:80-118`) driven by
  `FUNC(updateFusionFrame)` (`fnc_updateFusionFrame.sqf:33-75`). Discarded at
  the device edge by `FUNC(fusionFrameVisible)` and
  `FUSION_FRAME_MIN_INSET 0.97` (`script_component.hpp:10`;
  `fnc_updateFusionFrame.sqf:44-49`).
- Status: EXTRA.

### 5.3 Fusion emissive ladder

- Source: the whale_ecoti mods paint either a solid fill (W3/W4) or nothing.
- Ours: `addons/thermal_display/functions/fusion/fnc_applyFusionOverlay.sqf` carries a
  256-band emissive material ladder (header `:17-35`, files
  `data/fusion_emissive_000..255.rvmat`). The solid fill replaces it when the
  setting is on (`fnc_applyFusionFill.sqf:22-27`).
- Status: EXTRA.
- Deviation: our default look is graded physics; theirs is a flat block.

---

## 6. Biggest deviations, one paragraph

The four mods render a hot-target overlay by three mechanisms: a translucent
red-orange glass over the NVG (all four), a capsule-union orange silhouette on a
transparent map canvas or by `drawLine3D` (Mod A uses the canvas, W4/W3 use
`drawLine3D`), and a flat solid texture fill (W3/W4). Our code keeps the canvas
silhouette and the fill, and deletes the glass outright, because a HUD aid must
not tint the sensor image (`286fbdd`). Against Mod A specifically, our
`fnc_outlineDraw` ports the capsule topology, the sensor LOD and the occlusion
rays, but drops five source passes: the per-soldier gear radius, the backpack
inflation, the `_infl` sensor blur, the topology sweep budget/cache, and the
per-zone ray budget. It also hardcodes what the source exposes as settings:
brightness, opacity, whiteness, line width, far width, max outlines, glow,
sensor resolution, detail range, range, occlusion, HUD scale and grid
precision. Against FPANO (Mod B), our optics HUD ports the text layout, the
compass formatters, the marker labels and the rangefinder, but ships none of the
in-game HUD editor, the ACRE2/TFAR radio bridge, the three `CfgMarkers` icon
types, the sounds, or FPANO's 13 per-element visibility settings. Two of our
display layers have no source counterpart at all: the physical NVG phosphor tube
model in `fnc_applyNVGTubeModel.sqf` and the 256-band emissive thermal ladder.

## 7. Unknowns

- Mod A `fn_drawOutlines.sqf` lines 478-548 and 607-626 were only partly read;
  the glow draw and the exact soft-underlay width at `:549-606` were read by
  grep, not line by line. The presence and defaults of these passes are
  confirmed; the per-line arithmetic of the glow colour is UNKNOWN.
- W4 `fn_preInit.sqf`, `fn_postInit.sqf`, `fn_drawInfo.sqf` line bodies were not
  read in full. Their roles match section 1; exact line values are UNKNOWN.
- FPANO `FPANO_fnc_editor.sqf` lines 161-339 and `FPANO_fnc_radioBridge.sqf`
  lines 1-115, 173-312 were read by structure grep only. The functions are
  MISSING in ours regardless.
