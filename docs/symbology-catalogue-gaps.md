# AEE map symbology catalogue: dropped entries and non-emitted combinations

Companion to `docs/adr/ADR-024-nato-map-symbology.md`.  Records what the
catalogue build drops and why, so the counts stay honest.

Source of truth: `data/symbology/nato_catalogue.json`, built by
`tools/build_symbology_catalogue.py`.  The per-entry drops are in
`data/symbology/dropped.json`.

## 1. Entries dropped from the catalogue

The first pull admitted 1470 files.  An image is a symbol only when it carries
an APP-6 frame or a function glyph.  A war map, a historical unit insignia, an
article photograph, a logo or a guide is not a symbol and is dropped.

| Reason | Count | Example |
|---|---|---|
| not downloaded (Wikimedia CDN rate limit) | see dropped.json | `File:FRD GND.svg` |
| not a symbol: article image, map or insignia | see dropped.json | `File:1973 sinai war maps.jpg` |
| frame affiliation could not be resolved | 0 after re-derivation | none |
| a file that is not SVG or PNG | see dropped.json | `File:MapTerrano...` |

The drop reasons are recorded per entry in `data/symbology/dropped.json`.  The
validator `tools/validation/validate_symbology_catalogue.py` rejects a
catalogue entry with no frame and no glyph, so the junk cannot re-enter.

## 2. The re-derived `V` (Unspecified) entries

The first catalogue left 125 entries with the `V` affiliation prefix, because
the affiliation was not parsed.  They were article images, war maps and unit
insignia.  The build re-derives the affiliation from the title word and the
frame, and drops any entry it cannot resolve rather than guessing.

## 3. Combinations deliberately not emitted

The cross-product composes a function glyph into the four affiliation frames
AEE draws from the APP-6 geometry.  It does not emit a blind cartesian product.

| Not emitted | Reason |
|---|---|
| a glyph whose source has no separable frame | the glyph cannot be extracted; the framed original still ships |
| an affiliation with no function glyph | a frame with no glyph is not a symbol |
| the modifier combinations (echelon, strength, HQ, task force, feint) | the echelon and modifier assets ship as whole markers; composing every glyph x every modifier is a cartesian product the standard does not define as distinct symbols |

## 4. Standard facts carried as UNKNOWN

- `cadre` is not a MIL-STD-2525D field-F value (zero text hits).  Not drawn.
- The exact APP-6(E) Table 1-4 RGB is not held (APP-6 is RESTRICTED).
  MIL-STD-2525D Table XVI, the aligned public equivalent, is used.
- The `Detachment` echelon diverges between 2525D (platoon level) and APP-6C
  (squad level).  APP-6C is followed.

Sources: MIL-STD-2525D (10 June 2014, US Government public domain);
`/tmp/opencode/app6-grammar-reference.md`, `/tmp/opencode/app6-modifiers-reference.md`,
`/tmp/opencode/app6-catalogue-reference.md`.  Per JSP 945.
