# Arma 3 map-rendering surface + topographic map conventions

Research briefing for AEE. Compiled 2026-10-08.

Question answered: can AEE make the map a proper topographic map (water
shading, relief shading, contours, full legend), and what is the engine
ceiling?

Evidence base (primary files, not memory):
- Shipped `RscMapControl`: `the derapified ui_f.pbo config` lines 1272-1610
  (derapified from `A3/Addons/ui_f.pbo`).
- Eden map `ctrlMap`: `the derapified 3den.pbo config` lines 1037-1304
  (derapified from `A3/Addons/3den.pbo`).
- Strategic map `RscDisplayStrategicMap >> controlsBackground >> Map`:
  `ui_f.cpp` lines 38381-38438.
- Minimap / airborne minimap: `ui_f.cpp` lines 50285-50690.
- World map raster `CfgWorlds`: `the derapified map_altis.pbo config`
  lines 2265-2334 (derapified from `A3/Addons/map_altis.pbo`).
- Workshop mods unpacked with `hemtt utils pbo unpack -r`:
  `the unpacked Enhanced Map mod config`,
  `the unpacked Map Contour mod config`.
- Standards: `topo-standards.md` (sources cited there and in
  section 3 below).

Field semantics marked `[SHIPPED]` come from a shipped default. Semantics
marked `[INFERRED]` are not documented by Bohemia Interactive and are read
from the field name, the shipped default and the mod effect. Nothing is
invented.

---

## 1. The engine surface

Every field below is a **config field on a map control class**. All are
reachable from a mod by re-declaring the class (load-time, global). The
rendered terrain raster and the contour geometry are **not** control fields
and are not reachable (section 2).

Types: `colour[4]` = RGBA 0..1, `float`, `int`, `string`, `path`.

### 1.1 Fill colours (terrain and water)

| Field | Type | Shipped default (`RscMapControl`) | What it changes |
|---|---|---|---|
| `colorBackground` | colour[4] | `0.969,0.957,0.949,1` | Map paper / background where nothing is drawn. |
| `colorOutside` | colour[4] | `0,0,0,1` | Area outside the world bounds (outside terrain). |
| `colorSea` | colour[4] | `0.467,0.631,0.851,0.5` | Sea and inland water fill. |
| `colorForest` | colour[4] | `0.624,0.78,0.388,0.5` | Forest polygon fill (flat/vector mode). |
| `colorForestTextured` | colour[4] | `0.624,0.78,0.388,0.25` (declared on Eden `ctrlMap`; not on vanilla `RscMapControl`) | Forest fill in textured/close-zoom mode. A mod may add it to `RscMapControl`. |
| `colorForestBorder` | colour[4] | `0,0,0,0` | Forest polygon border line. |
| `colorRocks` | colour[4] | `0,0,0,0.3` | Rock / stony-area fill. |
| `colorRocksBorder` | colour[4] | `0,0,0,0` | Rock-area border line. |

### 1.2 Relief: contour and level lines

BI spells the interval field with its own typo (`Countour`). There is **no**
`colorContour` / `colorCountour`, **no** `sizeContour`, and **no**
`fontContour` field in the shipped configs. The real fields are:

| Field | Type | Shipped default | What it changes |
|---|---|---|---|
| `colorLevels` | colour[4] | `0.286,0.177,0.094,0.5` | The engine's elevation "level" lines (coarse relief lines). `[INFERRED]` — BI does not document it; shipped default is dark brown and the BHC contour mod sets it opaque black without blacking the map, so it is a line/overlay, not a fill. |
| `colorMainCountlines` | colour[4] | `0.572,0.354,0.188,0.5` | Index contour line (land). |
| `colorCountlines` | colour[4] | `0.572,0.354,0.188,0.25` | Intermediate contour line (land). |
| `colorMainCountlinesWater` | colour[4] | `0.491,0.577,0.702,0.6` | Index depth contour line (water). |
| `colorCountlinesWater` | colour[4] | `0.491,0.577,0.702,0.3` | Intermediate depth contour line (water). |
| `showCountourInterval` | int 0/1 | `0` | Shows/hides the contour-interval **label**. It does not set the interval value. |

### 1.3 Relief: shading and the satellite raster

| Field | Type | Shipped default | What it changes |
|---|---|---|---|
| `drawShaded` | float 0..1 | `0.25` on Eden `ctrlMap` (not declared on vanilla `RscMapControl`); minimap `0.1` | Strength of the engine's shaded-relief (hillshade) pass over the terrain raster. `[INFERRED]` |
| `shadedSea` | float 0..1 | `0.3` on Eden `ctrlMap`; not on vanilla `RscMapControl` | Strength of the shading pass over water. `[INFERRED]` |
| `maxSatelliteAlpha` | float 0..1 | `0.85` | Opacity of the baked satellite/map raster over the vector colours. |
| `alphaFadeStartScale` | float | `2` | Zoom scale where the satellite raster starts to fade out. |
| `alphaFadeEndScale` | float | `2` | Zoom scale where the satellite raster is fully faded. |

`drawShaded` and `shadedSea` are not declared in the vanilla `RscMapControl`
block, but they are valid tokens (present in the `ui_f.pbo` and `3den.pbo`
binaries) and the Eden `ctrlMap` sets them. The Enhanced Map mod adds
`drawShaded`/`shadedSea` to `RscMapControl` and they take effect.

### 1.4 Zoom, grid, roads, rail and labels

| Field | Type | Shipped default | What it changes |
|---|---|---|---|
| `scaleMin` / `scaleMax` / `scaleDefault` | float | `0.001` / `1` / `0.16` | Zoom range and start. |
| `colorGrid` / `colorGridMap` | colour[4] | `0.1,0.1,0.1,0.6` | Engine numeric grid lines (both layers). |
| `sizeExGrid` | float | `0.02` | Grid number size (`0` hides the numbers). |
| `fontGrid` | string | `TahomaB` | Grid number font. |
| `widthRailWay` | float | `4` | Rail line width. |
| `colorRailWay` | colour[4] | `0.8,0.2,0,1` | Rail colour. |
| `colorPowerLines` | colour[4] | `0.1,0.1,0.1,1` | Power line colour. |
| `colorRoads` / `colorRoadsFill` | colour[4] | `0.7,0.7,0.7,1` / `1,1,1,1` | Minor road line / fill. |
| `colorMainRoads` / `colorMainRoadsFill` | colour[4] | `0.9,0.5,0.3,1` / `1,0.6,0.4,1` | Main road line / fill. |
| `colorTracks` / `colorTracksFill` | colour[4] | `0.84,0.76,0.65,0.15` / `...,1` | Track line / fill. |
| `colorTrails` / `colorTrailsFill` | colour[4] | `0.84,0.76,0.65,0.15` / `...,0.65` | Trail line / fill. |
| `colorNames` | colour[4] | `0.1,0.1,0.1,0.9` | Place-name text colour. |
| `colorInactive` | colour[4] | `1,1,1,0.5` | Inactive/overlay tint. |
| `fontLabel`/`sizeExLabel`, `fontNames`/`sizeExNames`, `fontInfo`/`sizeExInfo`, `fontLevel`/`sizeExLevel`, `fontUnits`/`sizeExUnits` | string/float | e.g. `RobotoCondensed`, `0.02` | Label, name, info, level and unit text fonts and sizes. |
| `class Legend { x,y,w,h,color,colorBackground,font,sizeEx }` | — | positioned bottom-left | Positions/holds the engine map legend. The **content** is engine-drawn; this class does not let a mod author a legend body. |
| `class LineMarker`, `class Task`, `Waypoint`, `Bush`, `Rock`, `Tree`, `SmallTree`, `Bunker`, `Fortress`, `Ruin`, `Stack`, `Tourism`, `ViewTower`, `Cross`, `Chapel`, `Shipwreck`, `busstop`, `fuelstation`, `hospital`, `church`, `lighthouse`, `power*`, `quay`, `transmitter`, `watertower` | class | each has `icon`, `color[4]`, `size`, `importance`, `coefMin`, `coefMax` | Routes an engine object/location family to a marker icon, colour and size. (AEE already re-textures these to its own `.paa`.) |
| `text`, `idcMarkerColor`, `idcMarkerIcon`, `textureComboBoxColor`, `showMarkers`, `moveOnEdges`, `drawObjects` | mixed | `text="#(argb,8,8,3)color(1,1,1,1)"`, `-1`, `-1`, `1`, `1`, `0` (strategic) | Misc control plumbing. No terrain effect. |

There is **no** `texture` and **no** `textureCombat` field on any map control.
Searched `ui_f.cpp`, `3den_extract/config.cpp` and the `ui_f.pbo`,
`ui_f_exp_a.pbo`, `ui_f_decade.pbo`, `editor_f.pbo`, `functions_f.pbo`
binaries: NOT FOUND. The map image field is the world field `pictureMap`
(section 1.5).

### 1.5 Airborne-minimap-only fields

| Field | Type | Shipped default | Effect |
|---|---|---|---|
| `textureCompass`, `compassPos`, `compassSize` | path/array | `north_ca.paa`, `{-0.04,0}`, `{0.08,0.08}` | Compass rose. |
| `altitudeMapRange` | int | `100` | Range of the altitude colour map. |
| `altitudeMapColorLow` / `Mid` / `High` | colour[4] | `0,1,0,0.15` / `1,1,0,0.15` / `1,0,0,0.15` | A per-altitude tint ramp (green→yellow→red) on the airborne minimap only. This is the closest thing to a hypsometric tint in the engine, and it is a single 3-band ramp, not settable per elevation. |

### 1.6 World-level map fields (`CfgWorlds`, not the control)

The control reads these; a mod changes them only by redefining the world.

| Field | Example (Altis) | Effect |
|---|---|---|
| `pictureMap` | `A3\map_Altis\data\pictureMap_ca.paa` | The baked top-down map raster ("satellite" image) the control blends via `maxSatelliteAlpha`. |
| `pictureShot` | `ui_Altis_ca.paa` | Preview image. |
| `mapDrawingBrightnessModifier` | `1.5` | Multiplies map raster brightness. |
| `satelliteNormalBlendStart` / `End` | `10` / `100` | Normal-map blend distance. |
| `class OutsideTerrain { satellite, colorOutside }` | — | Outside-world fill and seabed. |
| `mapSize`, `mapZone`, `mapArea`, `longitude`, `latitude` | — | Map metadata. |
| `minHillsAltitude` / `maxHillsAltitude` | `80` / `200` | Hill/relief band limits. |
| `class Grid { offsetX, offsetY, class Zoom* { zoomMax, format, stepX/Y } }` | — | The engine numeric grid origin and step. **`RscMapControl` colours it only; the geometry is here.** |

### 1.7 Separate override targets

A `RscMapControl` re-declare does **not** reach every map. Confirmed
separate targets:

- `RscDisplayStrategicMap >> controlsBackground >> Map` — its own
  `RscMapControl` that re-declares colours and, in vanilla, sets
  `maxSatelliteAlpha = 1`, `alphaFade*=100`, `colorForest={1,1,1,1}`,
  `colorCountlines/mainCountlines/...Water={0,0,0,0}`, grid off.
- `ctrlMap` (Eden editor map) — class `ctrlMap`, not `RscMapControl`.
  `ctrlMapMain` and `ctrlMapEmpty` inherit it. Carries `drawShaded=0.25`,
  `shadedSea=0.3`, `colorForestTextured`, `runwayFont`, plus the full colour
  set.
- The minimap `CA_MiniMap` (`RscCustomInfoMiniMap`) and
  `RscCustomInfoAirborneMiniMap` override `maxSatelliteAlpha`, `alphaFade*`,
  the `ptsPerSquare*` densities, `colorSea`, `colorForest`, `drawShaded` and
  the altitude ramp.

A display that re-declares a field wins **for that display**. To change the
palette everywhere, set it on all four targets (AEE already does).

---

## 2. What shading is reachable — and the ceiling

The 2D map is composited from four layers:

1. **The baked map raster** (`CfgWorlds >> pictureMap`, a pre-rendered
   top-down image). `maxSatelliteAlpha` blends it over the vector colours.
   This raster is shipped with each world. A mod cannot replace it without
   redefining the world.
2. **Vector fills** from terrain data: sea, forest, rocks. Flat RGBA. There
   is **no per-elevation hypsometric tint ramp** and no tint bands; the only
   banded relief is the contour/level lines.
3. **Contour and level lines**, derived at runtime from the WRP heightmap.
   The **geometry and the interval are engine-derived and are not a config
   field**. Only the line colours (`colorCountlines`, `colorMainCountlines`,
   `color*Water`, `colorLevels`) and the interval *label* toggle
   (`showCountourInterval`) are settable. There is no contour line-width or
   font field.
4. **Shaded relief**: `drawShaded` (terrain) and `shadedSea` (water) apply a
   hillshade pass from the heightmap. They are strength multipliers 0..1.
   A mod **cannot supply its own hillshade texture**; it can only turn the
   engine's hillshade up, down or off.

**Can do:** set every fill, contour/level line colour, road/rail/power/track
colour, label font and size, grid colour and number size, satellite opacity
and fade, hillshade strength and sea-shading strength, and the world map
brightness (via `CfgWorlds >> mapDrawingBrightnessModifier`).

**Cannot do:** change the contour interval or the contour geometry; add a
hypsometric tint ramp (beyond the airborne minimap's 3-band altitude ramp);
replace the hillshade with custom art; replace the satellite raster; set
contour line width; author the engine legend body; add terrain shading that
is not the engine's one hillshade pass.

So a "proper topographic map" in this engine is: the engine's hillshade turned
up + well-chosen flat fill colours + coloured contour lines + labelled
interval + a scripted legend and grid overlay. The scripted legend (drawn in
SQF, like AEE's MGRS grid) is the only route to a real legend body.

---

## 3. The standards (published values only)

Full detail with per-value sources is in `topo-standards.md`.
Summary:

**Structural fact.** OS publishes colour values per product, not as one
palette. The openly citable numeric palettes are the OS product stylesheets on
GitHub. USGS and NATO publish colour **names**, not numbers.

**Ordnance Survey.**
- OS MasterMap Topography Layer (Outdoor style,
  `github.com/OrdnanceSurvey/OSMM-Topography-Layer-stylesheets`): inland/tidal
  water `#aadeef` (170,222,239); water line `#7ed2e0` (126,210,224);
  woodland `#cee6bd` (206,230,189); scrub/rough grassland `#e2efce`
  (226,239,206); building `#dcd7c6` (220,215,198); spot height `#857660`
  (133,118,96).
- Contours: OS MasterMap has none; contours are OS Terrain. Terrain 50 =
  **10 m interval** (`docs.os.uk`); Terrain 5 = 5 m. Contour colour from the
  OS Terrain 50 stylesheet `#E0945E` (224,148,94); OS Open Zoomstack Road
  style contour `#D6986B` (214,152,107).
- Road classes (OS Open Zoomstack, Road style,
  `github.com/OrdnanceSurvey/OS-Open-Zoomstack-Stylesheets`): motorway
  `#06B1CA`, primary `#37C256`, A `#FF889D`, B `#FFC073`, minor `#FEF2B4`.
- **Landranger/Explorer contour and road RGB: NOT PUBLISHED.** The leisure
  print colours are named "pink and orange" only.

**USGS / US Army.**
- USGS "Topographic Map Symbols" (pubs.usgs.gov/gip/TopographicMapSymbols)
  and the US Topo symbol guide give colours in **words**: contours brown,
  water blue, roads red and black, vegetation green, built-up gray/red. No
  RGB or hex is published.
- Contour intervals: 1:24,000 = 10 ft flat, up to 100 ft mountain, chosen
  per quad and printed in the margin; 1:50,000 metric 10–20 m.
- **Hypsometric tint band RGB: NOT PUBLISHED** by USGS. 7.5-minute quads do
  not use tints at all.
- US Army map reading (TC 3-25.26 / FM 3-25.26) uses the same conventions,
  reproduces symbols, publishes no RGB.

**NATO.**
- **STANAG 3675 Ed. 2** ("Symbols on Land Maps…") is a **symbol** standard,
  not a colour standard, and is **RETIRED** (DGIWG TCR-24-002, 28 Jun 2024:
  "Related to the retirement of STANAG 3675"; it also states STANAG 3675
  specifies no colours by numeric values).
- The colour standard is **DGIWG 131, "Printing Colours for Defence
  Geospatial Products"**, which is **not openly published**. Related:
  DGIWG 130 (web symbology), DGIWG 252 (Defence Topographic Map 1:50,000),
  STANAG 3677, STANAG 3600.
- AAP-6 is a glossary; APP-6 is symbology. **No NATO terrain/hypsometric RGB
  is openly published.**

**Never convert a published colour name to a number.** Where the authority
gives only a name, the name is the citable fact.

---

## 4. The two workshop mods

Both are **pure config, no new art**. Neither ships a texture. Ideas only. No
copy.

**Enhanced Map — `2467589125` (`DIS_enhanced_map`, author Hoplite).**
No licence stated in `mod.cpp`. Changes:
- `CfgLocationTypes` — recolours and resizes every place-name class
  (`Name`, `NameCity`, `NameMarine`, `Hill`, vegetation, `Strategic`…).
- `RscMapControl` — `maxSatelliteAlpha=1` (full baked raster),
  `drawShaded=0.15`, `shadedSea=1`, `showCountourInterval=1`,
  `scaleMax=1.3`, `scaleDefault=0.095`, `sizeExGrid=0.0375`,
  `sizeExLevel=0.03`, the `ptsPerSquare*` density set, `colorForestTextured`,
  a hand-tuned palette (sea `0,0.27,0.50,0.3`, forest `0.56,0.81,0,0.5`,
  roads orange/yellow, contours `0.73,0.48,0.31`).
- `RscDisplayStrategicMap >> controlsBackground >> Map` — same palette and
  sets most vector colours to alpha 0, keeping the satellite image.
- `ctrlMap` (Eden) — the same palette again.
Net effect: full satellite image plus mild hillshade plus restyled labels.

**BHC Map Contour — `1364777346` (`bhc_map_contour`, author Tomahawk,
bhc-clan.com).** No licence stated. Changes only `RscMapControl`:
`maxSatelliteAlpha=0.5` (damp the raster so lines read), `colorCountlines`
tan, `colorMainCountlines` red (index), `colorLevels` black, roads black
over yellow fill, tracks red over yellow. Net effect: a contour-line look on
a faded raster, from line colour alone.

The lesson from both: they move only the fields in section 1. Neither adds
contours, a tint ramp or a legend body, because the engine does not expose
them. What reads as "enhanced" is (a) full satellite raster, (b) hillshade
strength, (c) location-label styling.

---

## 5. What AEE should set, with source per value

AEE already sets (`addons/cartography/config_mapcolors.hpp`
and `config_mapdisplays.hpp`): `colorLevels`, `colorMainCountlines`,
`colorCountlines`, `colorMainCountlinesWater`, `colorCountlinesWater`, roads,
rail, power, tracks, trails, sea, forest, forestBorder, rocks, rocksBorder,
background, `maxSatelliteAlpha=0.35`, `showCountourInterval=1`, and it hides
the engine grid. It does **not** yet set `drawShaded`, `shadedSea` or
`colorForestTextured`.

Recommended, per the operator's four asks:

| Ask | Field(s) | Source for the value |
|---|---|---|
| Water shading | `colorSea` + `shadedSea` | Blue fill: name "water blue" (USGS Topographic Map Symbols; FM 21-31) and OS water `#aadeef`. AEE's current `0.55,0.70,0.85` is defensible; `shadedSea` is a model choice with no standard (Enhanced Map uses 1). |
| Terrain shading | `drawShaded` | No standard. The engine's own Eden map uses 0.25; Enhanced Map 0.15. This is the only route to relief shading. |
| Contours | `colorMainCountlines` / `colorCountlines` / `colorLevels` (+ the two water pairs) | Brown, from the USGS/FM 21-31 name "brown", matching OS contour `#E0945E`/`#D6986B`. AEE already sets brown. **The interval is not settable.** |
| Full legend | Engine `class Legend` cannot hold a body | AEE must draw its own SQF legend overlay (as it draws the MGRS grid, ADR-028). Engine gives no legend content. |
| Woodland, urban, rough ground | `colorForest`(+`colorForestTextured`), `colorRocks`, `colorForestBorder`/`colorRocksBorder` | OS: woodland `#cee6bd`, scrub/heath `#e2efce`, building `#dcd7c6`. AEE's current forest/rocks are close but not OS-sourced. |
| Outside-world fill | `colorOutside` | Vanilla is black. A sea/blue value (OS water `#aadeef` or `colorSea`) reads better at the map edge. |
| Satellite balance | `maxSatelliteAlpha` | No standard; lower (0.35–0.5) makes the vector topo colours read as a map; higher shows the photo raster. Operator intent ("topographic") favours lower. |

Ceiling to record for each: contour interval — engine-derived, NOT settable;
hypsometric tint — not available (only the airborne minimap's 3-band altitude
ramp); custom hillshade — not available; satellite raster — baked into the
world; legend body — must be scripted; grid geometry — `CfgWorlds`, only the
colour is controllable.

---

## 6. The density constants (`ptsPerSquare*`) and the object gate

Added 2026-10-09. No AEE value changed. This section records the shipped
baseline so the next worker does not repeat a wrong premise.

**The two shipped definitions.** The engine ships `RscMapControl` twice:

- `Dta/bin.pbo` (core, loads first): `Sea 6, Txt 8, CLn 8, Exp 8, Cost 8,
  For 4, ForEdge 10, Road 2, Obj 10`.
- `Addons/ui_f.pbo` (loads after): `Sea 5, Txt 20, CLn 10, Exp 10, Cost 10,
  For 9, ForEdge 9, Road 6, Obj 9`.

The config merge is last-loaded-wins per property, and the core loads before
the addons. So the ui_f re-declare WINS, and the in-game map uses its values.

**AEE is at parity.** `addons/cartography/config_mapcolors.hpp` sets exactly the
ui_f values (`Sea 5, Txt 20, CLn 10, For 9, ForEdge 9, Road 6, Obj 9`, and it
inherits `Exp 10, Cost 10`). It does not raise any density above the shipped
vanilla. The `ENG` source label in that header is correct.

**The direction is the opposite of the earlier note.** In
`CStaticMap::DrawBackground` (CWR `engine/Poseidon/UI/Map/UIMap.cpp`) the loops
stride by `iStep = toIntCeil(ptsPerSquareX * invPtsLand)` and advance by
`xStep = iStep * invLandRange * invScaleX`. The cell count is `w / xStep`, so
it is proportional to `1 / iStep`, that is `1 / ptsPerSquareX`. A HIGHER value
is a LARGER stride and FEWER per-frame draw calls. The forest, road and object
layers are gated the same way: `if (ptsLand >= ptsPerSquareFor)` draws only
when zoomed in, so a higher threshold draws less. To make the map faster the
values must go UP (coarser than vanilla), which is a quality tradeoff. Lowering
them makes the map slower. The earlier note "lower = fewer iterations" is
inverted.

**The object gate `drawObjects`.** This field is not in the CWR ancestor
source, where the object layer is gated only by `ptsLand >= ptsPerSquareObj`.
The token is present in the Arma 3 binaries (`arma3_x64.exe`,
`arma3server_x64.exe`). The shipped config sets it to `0` only on
`RscDisplayStrategicMap >> controlsBackground >> Map`, a whole-island overview
that must not draw scenery objects. The base `RscMapControl` does not carry
the field, so it keeps the engine default. This is consistent with a gate on
the scenery-object icon layer. The gate renders on the client only, so it
cannot be confirmed headless.

**The strategic map deviates (recorded, not changed).** AEE's shared include
carries the main-map densities into the strategic map, which its own vanilla
declaration sets to the coarse overview values (`Txt 20`, and `200` for
`CLn, Cost, For, ForEdge, Road, Obj`). Under the direction above, AEE's
strategic map is FINER than vanilla and so draws more per frame. The override
is deliberate (commit `b7fd2d37` sets "the object and line densities" on the
main map, the strategic map and the Eden map), so it is recorded here rather
than changed. The Eden `ctrlMap` matches its vanilla values already.

**Ceiling.** The map composite renders on the client. A headless server
resolves the config and proves the values, but it cannot measure the per-frame
cost. The operator is the only one who can judge the map look and the felt
cost.

Deliverable written: `topo-map-surface.md`.
