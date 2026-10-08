# ADR-026: The terrain and map-feature symbol layer

Status: accepted.

## Context

The map draws unit symbols from NATO APP-6, but it does not draw terrain and
map features as military topographic symbols. APP-6 and MIL-STD-2525 define
units, equipment, installations and military obstacles. They do not define
natural terrain. The terrain authority is a different standard family.
STANAG 3675, "Symbols on Land Maps, Aeronautical and Special Naval Charts"
(Edition 2, 15 June 2000), is that standard. The DGIWG Symbol Register,
product Defence Topographic Map (DTM50), succeeds it. The US Army FM 21-31
"Topographic Symbols" (1961) and the USGS "Topographic Map Symbols" sheet
(2005) are public-domain fallbacks with the same vocabulary.

STANAG 3675 is distribution-controlled and must not ship. The DGIWG register
graphics terms are UNKNOWN. AEE must draw or copy the standard geometry from a
public-domain source only.

The map draws location symbols from `CfgLocationTypes`, object icons from
`RscMapControl`, and the colours from `RscMapControl`. Every surface is a
load-time config re-declare. One re-declare reaches every map display.

## Decision

1. The terrain symbol authority is STANAG 3675, then the DGIWG Symbol
   Register (DTM50), with FM 21-31 and the USGS sheet as the public-domain
   fallback. See `docs/wiki/research/terrain-symbols.md`.
2. AEE uses REAL public-domain drawings. AEE does not hand-draw a terrain
   symbol. The drawings are cropped from FM 21-31 and the USGS sheet, recorded
   per symbol in `data/symbology/terrain_sources.json`, and re-textured to a
   white-on-transparent `.paa` so the engine colour tints the icon. A symbol
   that no source draws is recorded UNAVAILABLE, not invented.
3. The location symbols are a `CfgLocationTypes` re-declare. The eight icon
   classes carry an AEE topographic texture and the standard colour. The name
   and area classes carry the standard colour, size and label font. The
   `drawStyle` is unchanged.
4. The object icons are an `RscMapControl` re-declare, one nested class per
   engine object. The re-declare reaches only the objects the engine already
   routes to a class.
5. The map colours follow the standard palette: relief brown, water blue,
   vegetation green, roads red and white. The map registry is
   `data/symbology/terrain_symbols.json`.
6. Four display levers are adopted from prior art. `maxSatelliteAlpha` fades
   the baked satellite so the vector linework reads. The strategic map
   (`RscDisplayStrategicMap >> controlsBackground >> Map`) and the Eden map
   (`ctrlMap: ctrlDefault`) are separate override targets. Each location class
   carries a `font` and a `textSize`. `showCountourInterval` shows the contour
   interval label.
7. Eden and Zeus are in scope. `CfgCurator >> DrawGroup` draws a group marker
   per side from five side textures, and the engine points the civilian and
   unknown sides at the neutral frame. AEE re-declares the five side textures
   so they carry the real NATO symbol for the friend, hostile, neutral,
   civilian and unknown sides. The curator map control inherits
   `RscMapControl`, so the colours, the location symbols and the object icons
   reach Eden and Zeus with no separate re-declare.
8. The label font is the existing `AEEFont` family. No new font is added.

## Consequences

- The terrain layer is data-driven and observable. A generator writes the
  table, a validator checks the coverage, a test locks the config and the
  provenance, and Docker probe P112 reads the live merged config.
- No restricted document and no third-party graphic ships. The `.paa` are
  AEE's own rendering of a public-domain drawing.
- The engine ceilings are recorded. `drawStyle` is a fixed enum. The
  object-to-icon routing is engine-internal (BI ticket T157884). The contour
  geometry and interval are engine-derived. The road, rail and satellite
  layers are terrain data.
- A headless server renders no pixels. The visible map result needs one
  operator run.
- The hand-drawn terrain kernel from the original plan is not built. The
  operator required the real drawings, so the pure-kernel route was replaced
  by the real-image route.
