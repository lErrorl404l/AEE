# Arma 3 map grid: colour and geometry semantics

Compiled 2026-10-08. No AEE file was changed to produce it.

## Sources

- **ENGINE (primary):** `BohemiaInteractive/CWR`,
  `engine/Poseidon/UI/Map/UIMap.cpp`, function `CStaticMap::DrawGrid()`,
  lines 1971-2042.
  <https://github.com/BohemiaInteractive/CWR/blob/main/engine/Poseidon/UI/Map/UIMap.cpp>
  This is the Poseidon engine source (Arma: Cold War Assault - Remastered),
  the direct ancestor of Real Virtuality and the Arma lineage. The config
  schema (`colorGrid`, `colorGridMap`, `sizeExGrid`, `fontGrid`, CfgWorlds
  `Grid >> Zoom1/Zoom2`) is byte-identical to Arma 3. It is not the Arma 3
  binary, so each engine claim is labelled.
- **BIKI:** `drawLine`, `drawIcon`. The live wiki returns HTTP 403
  (Cloudflare). Quotes below are from the Wayback snapshots.
- **LOCAL CONFIG:** `the derapified core engine config (Dta/bin.pbo)` (RscMapControl
  at lines 20117-20160; `gridNumbersOverLines` at line 16403).

The BIKI `RscMapControl` page is **not available**: the live site is blocked,
and the Wayback CDX index holds **no snapshot** of that page. So there is no
verbatim BIKI description of `colorGrid`, `colorGridMap`, or `sizeExGrid`.
The engine source is the authority here.

## Q1. Which field colours the edge coordinate numbers?

**Answer: `colorGrid` colours the edge numbers. `colorGridMap` colours the
grid lines across the map body.**

`DrawGrid()` draws each horizontal and vertical grid line with
`_colorGridMap` (lines 2009-2010, 2030-2031), then draws the coordinate
number with `_colorGrid` (lines 2018, 2020, 2039, 2041):

```cpp
GridFormat(buffer, info->formatY, zSign == 1 ? z : z - 1);
...
GLOB_ENGINE->DrawText(Point2DFloat(left, top), _sizeGrid, ..., _fontGrid, _colorGrid, buffer);
GLOB_ENGINE->DrawText(Point2DFloat(right, top), _sizeGrid, ..., _fontGrid, _colorGrid, buffer);
```

So it is the **opposite** of the "colourGrid = lines" reading. `colorGrid` =
numbers (the map's coordinate ruler), `colorGridMap` = the in-map grid lines.

The vanilla values corroborate: `colorGrid = {0.15,0.15,0.05,0.9}` (numbers,
darker, alpha 0.9) and `colorGridMap = {0.25,0.25,0.1,0.75}` (lines, lighter,
alpha 0.75).

**Alpha 0:** `DrawText` renders the glyphs with the packed colour including
its alpha. With `colorGrid` alpha 0, the numbers draw fully transparent, so
they become **invisible**. Confidence: **High** (engine source); not verified
on the Arma 3 binary.

## Q2. What does `sizeExGrid` size?

**Answer: the edge coordinate numbers only.** There are no in-map line
labels. `_sizeGrid` is loaded from `sizeExGrid` (or `sizeGrid *
fontGrid->Height()` when `sizeGrid` exists, lines 279-289). It is used only
in `DrawGrid()` as the `DrawText` point size and as the vertical offset of
the number rows (lines 2001, 2014, 2018, 2020, 2039, 2041). It does not size
the grid lines.

A BIKI verbatim description could not be obtained (page unavailable).
Confidence: **High** (engine source).

## Q3. `drawLine [pos1, pos2, color, width]` - unit of `width`?

BIKI (`drawLine`, snapshot 2024-12-12) gives the syntax
`map drawLine [from, to, color, width]` and, verbatim:

> `width: Number - (Optional, default 3)`

BIKI states **no unit**. The engine draws map overlays in screen space
(`DrawLine(Line2DPixel ...)`, integer pixel coordinates). The sibling command
`drawIcon` is documented by the community as zoom-independent (see Q4).
Inference: `width` is **screen pixels**, and it is **not affected by map
zoom**. Confidence: **Medium** (BIKI silent; inferred from the pixel render
path and the `drawIcon` behaviour). Treat the pixel/zoom-independent claim as
unproven for `drawLine` specifically.

## Q4. `drawIcon [...]` - units of `width`/`height` and `size`?

BIKI (`drawIcon`, snapshot 2023-10-13), verbatim:

> `width: Number - width of the icon (but not the text)`
> `height: Number - height of the icon (but not the text)`
> `textSize: Number - (Optional, default -1) size of the text in UI units`

The parameter named `size` in the question is `textSize`.

- `width`/`height`: **screen pixels, not world metres, not map-relative.**
  BIKI does not name the unit, but the note by Leopard20 (2022-05-09) states:
  "The icon size always stays the same, even after zooming in/out." He gives
  the conversion to a world size: `_scale = 6.4 * worldSize / 8192 *
  ctrlMapScale _map; _size = _sizeInMeters / _scale`. So an icon keeps a
  constant pixel size while the map zooms.
- `textSize`: **UI units** (BIKI, verbatim above).

Confidence: **High** for `textSize` (BIKI verbatim) and for the pixel nature
of `width`/`height` (community note + engine pixel space).

## Q5. Do the numbers draw at `colorGrid` alpha 0? Any separate toggle?

**No, they become invisible.** The engine calls `DrawText` for the numbers
regardless of colour (Q1), but alpha 0 renders them transparent. `sizeExGrid
> 0` does not override that. Likewise `sizeExGrid = 0` alone also hides them
(zero-height text).

**No documented separate visibility toggle** exists on `RscMapControl`. There
is no `showGrid` field in the config.

`gridNumbersOverLines` is a **world-class** field (`CfgWorlds >>
DefaultWorld`, local config line 16403, value 0), not an `RscMapControl`
field. Its meaning could not be confirmed from a primary source (BIKI page
absent; no reader found in the CWR source). By its name it most likely
controls **draw order** (numbers drawn over the lines), not visibility.
Status: **UNKNOWN - inference only.**

The world `Grid >> format/formatX/formatY/stepX/stepY` fields control the
**number format and step** (for example `"Aa"` / `"00"` vs `"A"` / `"0"`),
not visibility.

## Consequence for AEE (load-bearing)

AEE sets `colorGrid[] = {0,0,0,0}` at
`addons/cartography/config_mapdisplays.hpp:27,40` and
`addons/thermal/RscTitles.hpp:72`, with `sizeExGrid = 0.02`. If the CWR
mapping holds for Arma 3, that alpha 0 hides the edge numbers as well as the
lines. To restore the engine coordinate numbers while keeping the engine
lines off, set `colorGrid` alpha > 0 and keep `colorGridMap` alpha 0.
Confidence: **Medium-High** (engine-source mapping, Arma 3 binary unverified).

## Verdict / confidence summary

| Q | Answer | Confidence |
|---|--------|-----------|
| 1 | `colorGrid` = edge numbers; `colorGridMap` = grid lines. alpha 0 hides the numbers. | High (engine) |
| 2 | `sizeExGrid` sizes the edge numbers only. | High (engine) |
| 3 | `drawLine` width = screen pixels, zoom-independent. | Medium (inference) |
| 4 | `width`/`height` = pixels (zoom-independent); `textSize` = UI units. | High |
| 5 | No separate toggle. alpha 0 hides the numbers. `gridNumbersOverLines` meaning UNKNOWN (likely draw order). | High for alpha; Low for the field |
