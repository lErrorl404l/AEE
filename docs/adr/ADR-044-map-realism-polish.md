# ADR-044: Map realism polish

Status: Accepted
Date: 2026-10-10

Decision: AEE audits its own map surface, adopts four techniques from the
studied Workshop mods as AEE's own code, and keeps the real open-domain APP-6
marker set. A pure kernel holds an icon at a fixed world size at every zoom. A
killed unit keeps a last-known contact. An optional device gate hides the unit
symbols without a carried tracker. A scripted legend draws the map palette.
Every new value is sourced, derived, or marked UNSOURCED.

## Context

The AEE map layer is a load-time re-texture of the engine's own location and
object classes (ADR-023, ADR-026, ADR-028, ADR-030). The engine draws the
contour, road, rail and satellite geometry. A mod reaches only the config
fields the engine re-declares, and a headless server renders no pixels.

Four Workshop mods were studied: DIS Enhanced Map (2467589125), APP6 Markers
(3009271265), VKing (964303647) and Real Map (3532429203). Their licences are
UNKNOWN or RESTRICTIVE (docs/engine/workshop-mod-licence-survey.md). AEE takes
the technique only. It imports no image, config or script from a mod.

The audit found that the AEE surface reaches the main map, the briefing, the
GPS, the Eden map and the strategic map in full. The minimap and the airborne
minimap each re-declare part of the palette, so the engine override wins for
the fields it names. Two engine records were stale against the shipped config.

## Decision

1. The scale-invariant world-size icon kernel. `FUNC(mapIconWorldSize)`
   converts a desired world-metre size to the `drawIcon` pixel width and
   height, by `pixels = metres / (6.4 * worldSize / 8192 * scale)`. The kernel
   is pure: the world size and the scale arrive as arguments. The constants
   6.4 and 8192 are UNSOURCED, because no primary engine source publishes
   them. Technique from APP6 Markers, reimplemented.

2. The last-known contact lifecycle. `FUNC(symbologyKilledMarker)` maps a live
   unit's resolved spec to the last-known spec, which keeps the same
   affiliation and category. An `EntityKilled` handler records the death
   position. A dead in-range unit therefore stays on the map. Technique from
   VKing, reimplemented.

3. The blue-force-tracker device gate. `FUNC(symbologyHasTracker)` reports
   whether a carried-item list holds a tracker device. The setting
   `aee_symbology_bftRequired` (default false) skips the unit pass when the
   player carries no tracker. The default is off, so nothing regresses.
   Technique from VKing, reimplemented.

4. The display levers AEE left at the vanilla value. `scaleMax = 2` is AEE's
   own, UNSOURCED. `scaleDefault = 0.3` is the engine strategic-map scale
   (`ui_f.pbo`). The LOD and simple density fields adopt the engine Eden
   `ctrlMap` values (`3den.pbo`): `ptsPerSquareForLod1 = 4`,
   `ptsPerSquareForLod2 = 1`, `ptsPerSquareMainRoad = 6`,
   `ptsPerSquareMainRoadSimple = 1`, `ptsPerSquareRoadSimple = 1`,
   `ptsPerSquareObjLod1 = 2`. Technique from DIS Enhanced Map; the values are
   AEE's own.

5. The scripted topographic legend. The engine `Legend` class holds no body,
   so `FUNC(mapLegendDraw)` returns the legend rows and the Draw hook draws
   them. Every swatch colour resolves from the palette argument, which the
   caller builds from `data/symbology/terrain_symbols.json`. The legend and
   the map therefore share one source.

6. The minimap reach. AEE re-declares the minimap and airborne-minimap fields
   the engine does not force, from `config_mapminimap.hpp`. Every reachable
   value is the same as `config_mapcolors.hpp`. The engine keeps its own sea
   fill, forest fill and satellite fade on those two displays. The ceiling is
   recorded in the file header.

7. No marker art is generated or imported. The marker set stays the real
   Commons-derived APP-6 set already shipped. No restricted asset is used.

## Consequences

- The map holds the same real APP-6 symbols. The four techniques are AEE's own
  code, so the licence boundary holds.
- A unit symbol keeps its ground size at every zoom, and a destroyed unit
  stays as a last-known contact.
- The tracker gate ships off, so the default behaviour does not change.
- The engine owns the contour geometry, the contour interval, the satellite
  raster, the hillshade and the road geometry. AEE changes only the colours,
  the label sizes, the shading strength and the density constants.
- A headless server renders no pixels, so the visible map result needs one
  operator run. The operator-only checks are the legend, the zoom range, the
  destroyed contact, the tracker gate and the minimap.

## References

- ADR-023 (NATO map symbology), ADR-026 (terrain map symbols) and ADR-028
  (map defects).
- ADR-030 (map legibility, location inheritance and the MGRS contrast).
- `docs/wiki/research/map-surface-audit.md` (the surface reach) and
  `docs/wiki/research/map-qa-matrix.md` (the invariant-to-check matrix).
- `docs/engine/map-baseline.md` (the vanilla baseline and the AEE delta) and
  `docs/engine/topo-map-surface.md` (the rendered-map surface).
- `docs/engine/workshop-mod-licence-survey.md` (the per-mod licence facts).
- `tools/tests/test_map_qa.py` (the machine checks and the mutation proofs).
