# NATO and OPFOR map symbology source register

Read-only record of the standards behind the AEE map symbology layer. The
symbol kernels read this register. No code changed to produce it.

- Repo: AEE. The register cites public sources only and embeds no local path.
- Method: the primary APP-6(C) PDF, the STANAG 2019 Edition 7 PDF and the
  MIL-STD-2525 ASSIST record.
- Every row carries a grade. A **sourced** row is a published value. A
  **derived** row follows a formula from a published value. An **UNSOURCED**
  row is a model choice that no source supports.

## 1. Standards

| Standard | Edition | Date | Status | Grade | Source |
|---|---|---|---|---|---|
| NATO APP-6 | (C) | May 2011 | NATO UNCLASSIFIED, reachable primary | sourced | `https://ia601602.us.archive.org/22/items/23-miscellanea/APP-6%28C%29%20NATO%20Joint%20Military%20Symbology%20-%20May%202011.pdf` |
| STANAG 2019 | Edition 7 | 16 October 2017 | NSO(JOINT)1231(2017), encloses APP-6(D) | sourced | `https://www.jedi-sec.us/downloads/MISC_PDF/2019EFed07.pdf` |
| NATO APP-6 | (E) | current | named only, no NATO access | UNSOURCED | none |
| MIL-STD-2525 | Revision E Change 1 | 02 March 2025 | US alignment, ASSIST record | sourced | `https://quicksearch.dla.mil/qsDocDetails.aspx?ident_number=114934` |

APP-6(C) is the reachable primary. STANAG 2019 Edition 7 encloses APP-6(D).
APP-6(E) is named as current and no copy is reachable without NATO access.
MIL-STD-2525 is the US alignment.

## 2. Frame grammar

The affiliation sets the base shape. The dimension sets the modifier.

| Affiliation | Base shape | Grade | Source |
|---|---|---|---|
| friend | rectangle | sourced | APP-6(C) |
| hostile | diamond, the rectangle on a point | sourced | APP-6(C) |
| neutral | square | sourced | APP-6(C) |
| unknown | quatrefoil | sourced | APP-6(C) |

| Dimension | Frame modifier | Grade | Source |
|---|---|---|---|
| land | closed frame | sourced | APP-6(C) |
| sea surface | closed frame | sourced | APP-6(C) |
| air | arc on the top edge | sourced | APP-6(C) |
| subsurface | curved bottom edge | sourced | APP-6(C) |
| space | filled apex | sourced | APP-6(C) |
| installation | filled top bar | sourced | APP-6(C) |
| equipment | circle | sourced | APP-6(C) |

APP-6(C) gives the sea surface a closed frame. MIL-STD-2525 gives the sea
surface a hull arc. The register keeps the APP-6 closed frame and records the
hull arc as a named per-2525 variant.

## 3. Colour table

The colour table is APP-6(C) Table 1-4. The values are RGBA in the range 0 to
1. AEE uses the display values below.

| Meaning | RGBA | Grade | Source |
|---|---|---|---|
| friend | 0, 1, 1, 1 cyan | sourced | APP-6(C) Table 1-4 |
| hostile | 1, 0, 0, 1 red | sourced | APP-6(C) Table 1-4 |
| neutral | 0, 1, 0, 1 neon green | sourced | APP-6(C) Table 1-4 |
| unknown | 1, 1, 0, 1 yellow | sourced | APP-6(C) Table 1-4 |
| lines and text | 0, 0, 0, 1 black | sourced | APP-6(C) Table 1-4 |
| high contrast | 1, 1, 1, 1 white | sourced | APP-6(C) Table 1-4 |

The OPFOR palette swaps the friend and hostile values. That swap is a derived
row. The neutral and unknown values do not change.

## 4. Echelon table

The echelon table is APP-6(C) Table 3-7.

| Echelon | Symbol | Grade | Source |
|---|---|---|---|
| team | diameter | sourced | APP-6(C) Table 3-7 |
| squad | dot | sourced | APP-6(C) Table 3-7 |
| section | two dots | sourced | APP-6(C) Table 3-7 |
| platoon | three dots | sourced | APP-6(C) Table 3-7 |
| company | bar | sourced | APP-6(C) Table 3-7 |
| battalion | two bars | sourced | APP-6(C) Table 3-7 |
| regiment | three bars | sourced | APP-6(C) Table 3-7 |
| brigade | X | sourced | APP-6(C) Table 3-7 |
| division | XX | sourced | APP-6(C) Table 3-7 |
| corps | XXX | sourced | APP-6(C) Table 3-7 |

## 5. Text fields

The text field table is APP-6(C) Table 3-2.

| Field | Meaning | Grade | Source |
|---|---|---|---|
| T | unique designation | sourced | APP-6(C) Table 3-2 |
| M | higher formation | sourced | APP-6(C) Table 3-2 |
| X | altitude | sourced | APP-6(C) Table 3-2 |
| Z | speed | sourced | APP-6(C) Table 3-2 |

## 6. Visual cross-check and honesty notes

The Wikimedia Commons page `NATO_Military_Map_Symbols` is a visual
cross-check only. Its content carries the licences that the page states. No
image from that page is downloaded, vendored or shipped in AEE.

Two honesty notes.

1. The frame rules follow APP-6(C). MIL-STD-2525 gives the sea surface a hull
   arc where APP-6 gives a closed frame. AEE follows APP-6 and labels the arc
   variant per-2525.
2. The function glyph geometry is not transcribable from text. The standard
   names the function icons. It gives no coordinates. AEE ships a curated set
   of about twenty glyphs and marks each glyph derived or UNSOURCED.

## 7. Marker asset sources

The symbols are real engine map markers. Every marker is a `CfgMarkers` entry
with a real `.paa` icon. The assets come from two sources.

The engine's own NATO textures, referenced and not copied, under
`\A3\ui_f\data\map\markers\nato\`. The `b_`, `o_` and `n_` families carry the
friend, hostile and neutral frames. The engine ships these glyphs per family:
`unknown`, `inf`, `motor_inf`, `mech_inf`, `armor`, `recon`, `air`, `plane`,
`uav`, `naval`, `med`, `art`, `mortar`, `hq`, `support`, `maint`, `service`,
`installation`, `antiair`. The reference is a load-time path, so no engine file
is redistributed.

The AEE produced textures, under `addons/optics/data/markers/`, for the
symbols the engine set does not carry: the whole unknown-affiliation `u_`
family, and the engineer, signal, supply, subsurface and waypoint glyphs. That
is 35 files. The generator `tools/gen_symbology_markers.py` renders each one
from the pure frame and icon kernels through `tools/tests/sqf_lite.py`, so the
texture and the drawn symbol share one source of truth. The texture is white on
transparent, so the engine marker colour tints it the way it tints the vanilla
NATO markers. The generator converts the render to a PAA with
`hemtt utils paa convert`.

Licence. No `.paa` from a Workshop mod is used. The three studied mods do not
permit reuse. The engine `.paa` are referenced, not copied. The produced `.paa`
are AEE's own rendering of the public geometry. The MIL-STD-2525 frame and
glyph geometry is US Government work and is public domain.
