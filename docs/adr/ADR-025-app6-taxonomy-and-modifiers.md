# ADR-025: The MIL-STD-2525 taxonomy marker layer and the missing modifiers

Status: accepted.

## Context

The pulled Commons catalogue holds the drawn APP-6 gallery. It does not hold the
standard's full function-glyph taxonomy. Coverage of the 195 distinct
MIL-STD-2525C Ground/Unit glyph names was 82 of 195 (42 percent). The Air, Sea
Surface, Subsurface and Space branches were thin. AEE held no mission-task
graphic, no strength or feint modifier, no standalone task-force bracket, no
standalone HQ staff line and no per-affiliation installation modifier. The
civilian colour was neutral green, not magenta. The echelon assets were whole
markers and did not sit above the frame.

## Decision

1. The missing function glyphs come from the MIL-STD-2525 taxonomy
   (`/tmp/opencode/symbol_army_rows.tsv`, 877 rows, name and SIDC and
   hierarchy). A row whose function the catalogue already covers is skipped, so
   the real pulled image wins. The rest are rendered from their SIDC by
   milsymbol 3.0.4 (MIT), in monochrome so the engine marker colour tints the
   texture. The symbol designs are the standard's geometry (public domain). See
   `ATTRIBUTION-taxonomy.md` and `LICENCE-milsymbol.txt`.
2. The mission tasks, the modifiers and the echelon overlays are drawn by AEE
   from the standard. The mission tasks are MIL-STD-2525D TABLE H-XXIV plus the
   FM 3-90 Appendix B graphics. A task with no standard graphic is recorded in
   `data/symbology/modifiers.json` and is not drawn.
3. The civilian colour is magenta (MIL-STD-2525D Table XVI, RGB 255, 0, 255).
4. The echelon is layered, not composed into each frame `.paa`. Composition
   would multiply the marker count by the echelon ladder for every unit symbol.
   Each `AEE_Ech_*` texture holds the ticks in the top band of a 64 by 128
   canvas, so it sits above a frame marker placed at the same position.

## Consequences

- The marker set is complete against the standard taxonomy, not only the drawn
  Commons gallery.
- A new generator depends on Node and milsymbol at generation time. The
  committed textures and headers do not. The generator names the module path in
  `MILSYMBOL_ENTRY`.
- The mission-task set is smaller than the FM 3-90 list, because the standard
  defines no graphic for six of the tasks. Each is recorded with its reason.
