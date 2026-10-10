# The vanilla map baseline and the AEE deltas

This record states how vanilla Arma builds the 2D map, field by field, and what
AEE changes per field. It names a PBO and a line, never a path on one machine.
Read it before any map config change.

The engine ships `RscMapControl` twice. The core, `Dta/bin.pbo`
(`config.cpp:20117`), loads first. `Addons/ui_f.pbo` (`config.cpp:1272`)
re-declares it and loads after. The config merge is last-loaded-wins per
property, so the `ui_f` values win in game. This record uses the `ui_f` block
as the vanilla baseline.

## 1. The render pipeline

`CStaticMap::OnDraw` composites four layers every frame (open-sourced Poseidon
engine, `UI/Map/UIMap.cpp`):

1. The baked satellite raster (`CfgWorlds >> pictureMap`), blended over the
   vector colours by `maxSatelliteAlpha`.
2. The vector fills from terrain data: sea, forest and rocks. Flat RGBA.
3. The contour and level lines, derived at run time from the WRP heightmap.
4. The hillshade pass: `drawShaded` for the terrain and `shadedSea` for the
   water, both strength multipliers.

A mod cannot replace the raster, the fill geometry, the contour geometry or
the hillshade texture. It sets the colours, the shading strength and the
satellite opacity.

## 2. The `RscMapControl` fields

The vanilla column is `Addons/ui_f.pbo` `config.cpp:1272`. The AEE column is
`addons/cartography/config_mapcolors.hpp`, included inside the
`RscMapControl` block in `addons/cartography/config.cpp:65`.

| Field | Vanilla (`ui_f.pbo:1272`) | AEE | AEE source |
|---|---|---|---|
| `colorBackground` | `0.969,0.957,0.949,1` | `0.90,0.88,0.80,1` | FM 21-31; USGS |
| `colorOutside` | `0,0,0,1` | `0.90,0.88,0.80,1` | FM 21-31; USGS |
| `colorSea` | `0.467,0.631,0.851,0.5` | `0.55,0.70,0.85,1` | DGIWG water blue |
| `colorForest` | `0.624,0.78,0.388,0.5` | `0.55,0.74,0.44,1` | FM 21-31; DGIWG green |
| `colorForestBorder` | `0,0,0,0` | `0,0.5,0,1` | FM 21-31 |
| `colorForestTextured` | not set on the base | `0.45,0.66,0.34,0.30` | OS woodland fill `#cee6bd` |
| `colorRocks` | not set | `0.75,0.70,0.60,1` | FM 21-31 |
| `colorLevels` | `0.286,0.177,0.094,0.5` | `0.70,0.48,0.32,1` | FM 21-31 relief brown |
| `colorMainCountlines` | `0.572,0.354,0.188,0.5` | `0.45,0.26,0.12,1` | FM 21-31 brown |
| `colorCountlines` | `0.572,0.354,0.188,0.25` | `0.62,0.42,0.22,1` | FM 21-31 brown |
| `colorMainCountlinesWater` | `0.491,0.577,0.702,0.6` | `0,0.5,0.75,1` | DGIWG water blue |
| `colorCountlinesWater` | `0.491,0.577,0.702,0.3` | `0.30,0.60,0.80,1` | DGIWG water blue |
| `colorNames` | `0.1,0.1,0.1,0.9` | `0.10,0.10,0.10,0.90` | FM 21-31; USGS |
| `colorGrid` | `0.1,0.1,0.1,0.6` | `0,0,0,0` | engine grid off (ADR-028) |
| `colorGridMap` | `0.1,0.1,0.1,0.6` | `0,0,0,0` | engine grid off (ADR-028) |
| `sizeExGrid` | `0.02` | `0.04` | AEE MGRS label size |
| `maxSatelliteAlpha` | `0.85` | `0.5` | AEE model choice (ADR-030) |
| `drawShaded` | not set on the base | `0.15` | Enhanced Map idea (ADR-030) |
| `shadedSea` | not set on the base | `1` | Enhanced Map idea (ADR-030) |
| `showCountourInterval` | `0` | `1` | the interval label is shown |
| `alphaFadeStartScale` | `2` | `2` | engine value kept |
| `alphaFadeEndScale` | `2` | `2` | engine value kept |
| `fontLevel` | `TahomaB` | `RobotoCondensed` | engine field, AEE label family |
| `sizeExLevel` | `0.02` | `0.04` | doubled for legibility |
| `scaleMin` | `0.001` | not set | AEE leaves it to the engine |
| `scaleMax` | `1` | not set | AEE leaves it to the engine |
| `scaleDefault` | `0.16` | not set | AEE leaves it to the engine |
| `ptsPerSquareSea` | `5` | `5` | ui_f parity |
| `ptsPerSquareTxt` | `20` | `20` | ui_f parity |
| `ptsPerSquareCLn` | `10` | `10` | ui_f parity |
| `ptsPerSquareFor` | `9` | `9` | ui_f parity |
| `ptsPerSquareForEdge` | `9` | `9` | ui_f parity |
| `ptsPerSquareRoad` | `6` | `6` | ui_f parity |
| `ptsPerSquareObj` | `9` | `9` | ui_f parity |
| `ptsPerSquareExp`, `ptsPerSquareCost` | `10` | inherited | ui_f parity |

The AEE density values are the `ui_f` values, not above them. The `ptsPerSquare*`
density is a per-frame cost lever: a HIGHER value is a LARGER stride and FEWER
draw calls (`CStaticMap::DrawBackground`). AEE raises no density above vanilla.

The `colorBackground` alpha stays 1, so the map ground is opaque. The engine
minimap overrides `colorBackground` with the profile background colour, so the
AEE value does not reach it.

## 3. The separate override targets

A `RscMapControl` re-declare does not reach every map. The separate targets:

- `RscDisplayStrategicMap >> controlsBackground >> Map` (`ui_f.pbo:38381`).
  Its own `RscMapControl`. Vanilla sets `maxSatelliteAlpha` from a uinamespace
  default of `1` and `scaleMin/Max/Default` to `0.3`. AEE re-declares the same
  topographic surface (`addons/cartography/config_mapdisplays.hpp:22`).
- `ctrlMap` (Eden, `Addons/3den.pbo:1037`). Not `RscMapControl`. Vanilla sets
  `drawShaded = 0.25`, `shadedSea = 0.3`, `maxSatelliteAlpha = 0.85` and
  `colorForestTextured = 0.624,0.78,0.388,0.25`. `ctrlMapMain` and
  `ctrlMapEmpty` inherit it. AEE re-declares the surface
  (`config_mapdisplays.hpp:39`).
- The minimap `RscCustomInfoMiniMap >> controls >> MiniMap >> Controls >>
  CA_MiniMap` (`ui_f.pbo:50285`). Vanilla overrides `maxSatelliteAlpha` (0),
  `alphaFade*` (10), the `ptsPerSquare*` densities, `drawShaded` (0.1),
  `colorSea` and `colorForest`, and turns the contour interval label off. AEE
  does not re-declare it, so the engine override wins.
- The airborne minimap `RscCustomInfoAirborneMiniMap` (`ui_f.pbo:50644`)
  inherits the minimap and overrides `colorSea`, `colorForest`, `drawShaded`
  and the altitude ramp.
- The curator map `RscDisplayCurator >> ControlsBackground >> Map` inherits
  `RscMapControl`, so the AEE surface reaches it with no separate re-declare
  (`addons/cartography/config_curator.hpp`).

A display that re-declares a field wins for that display. The live probe P142
reads the reach per surface.

## 4. The `CfgLocationTypes` inheritance graph

The engine draws a place-name or an icon from `CfgLocationTypes`. `Mount`,
`Name` and `Area` are the parentless roots. `Strategic` derives from `Name`,
and `Hill` derives from `Name`. Every AEE re-declared class restates its parent
(`addons/cartography/config_locationtypes.hpp`), because a bare reopen invokes
the engine Empty syntax and strips `drawStyle` and the base texture (ADR-030).
The full graph is in `docs/wiki/research/map-qa-matrix.md`.

`drawStyle` is a fixed engine enum (`name`, `icon`, `area`, `mount`). A mod
changes the texture, colour, size, font, shadow and importance only.

## 5. The `CfgMarkers` and `CfgMarkerClasses` surface

`CfgMarkers` holds the map symbols. `CfgMarkerClasses` groups them for the
picker. AEE re-declares each engine marker family with an AEE `.paa` under
`addons/symbology/data/markers/` (`addons/symbology/config_markers.hpp:7251`)
and declares the AEE categories in `CfgMarkerClasses`. The set is the real
Commons-derived APP-6 set. `Empty` and `EmptyIcon` stay invisible.

## 6. The `CfgWorlds >> Grid` geometry

The engine numeric grid geometry is a world field, not a control field. Each
world declares `class Grid` with `offsetX`, `offsetY` and one `class Zoom*`
per zoom band, each carrying `zoomMax`, `format`, `stepX` and `stepY`. The
control colours the grid only. AEE cannot move the geometry, so it turns the
engine grid off and draws the cardinal AEE MGRS overlay instead (ADR-028,
ADR-030). The per-world `Grid` values are UNKNOWN in this record: they ship in
each world PBO and were not read for this baseline.

## Related records

- `topo-map-surface.md` - the rendered-map fields a mod controls.
- `arma-map-grid-semantics.md` - the grid colour and geometry fields.
- `topo-standards.md` - the published colour values and contour intervals.
- `docs/wiki/research/map-surface-audit.md` - the live reach per surface.
- `docs/wiki/research/map-qa-matrix.md` - the invariant to machine-check map.

