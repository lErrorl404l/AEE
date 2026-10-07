# ADR-024: NATO map symbology - the sourced frame grammar, the pure kernels and the ceiling

Status: Accepted

## Context

The engine draws map markers as small coloured icons. The icon shape shows the
marker family. It does not show the affiliation as a frame, the battle
dimension, or the function class. The engine also draws a 3D unit icon in the
world. A commander therefore cannot read a formation at a glance.

The operator asked for NATO and OPFOR symbology on the map and in the world,
with a selectable affiliation, and for the AEE font on the labels.

AEE draws its own symbols. The engine marker and icon surface has limits, and
this record states them. The engine 3D unit icon cannot be removed. The full
APP-6 icon library holds thousands of glyphs. AEE draws a curated vector set
instead and states the ceiling.

The symbology uses published standards. The frame grammar and the colours come
from NATO APP-6(C) of May 2011. STANAG 2019 Edition 7 of October 2017 encloses
APP-6(D). MIL-STD-2525 Revision E Change 1 of March 2025 is the US alignment.
The frame shapes, the dimension modifiers and the Table 1-4 colours are read
from these documents. No glyph coordinate is published, so each vector glyph is
a derived or UNSOURCED approximation and is marked as such.

## Decision

### The standard

The layer follows APP-6(C) as the primary standard. It names the frame grammar,
the dimension modifiers and the Table 1-4 display colours. STANAG 2019 and
MIL-STD-2525E align on the same grammar, so the layer also serves a force that
uses either document. The Wikimedia Commons NATO symbol set was a visual
cross-check only. No image is vendored.

### The frame grammar

The base shape comes from the affiliation. A friend symbol is a rectangle, a
hostile symbol is a diamond, a neutral symbol is a square and an unknown symbol
is a quatrefoil. The dimension modifier changes one edge. A land or sea symbol
keeps the closed frame. An air symbol has a domed top edge. A subsurface symbol
has a curved bottom edge. A space symbol adds a filled apex. An installation
symbol adds a filled top bar. An equipment symbol is a circle.

The arc samples use a parabola. The standard gives no curve equation, so the
arc is a derived approximation. The frame stays inside the unit box [-1, 1].

### The Table 1-4 colours

`fnc_symbolPalette` maps an affiliation and a palette to one RGBA colour. The
values are APP-6(C) Table 1-4. Friend is cyan `[0, 1, 1, 1]`, hostile is red
`[1, 0, 0, 1]`, neutral is green `[0, 1, 0, 1]` and unknown is yellow
`[1, 1, 0, 1]`.

### The palette affiliation switch

The setting `aee_optics_symbologyPalette` chooses NATO, OPFOR or Auto. The NATO
palette fixes WEST as friend. The OPFOR palette swaps the friend and the hostile
colour, so a red OPFOR force reads as friendly. Auto follows the local side. The
adapter `fnc_symbologyPaletteFriendly` resolves Auto against the local side
before the pure call, so the kernel stays pure.

### The pure kernels and the resolver

Five pure kernels carry the grammar. Each takes its inputs as arguments and
reads no setting, no marker, no unit and no world.

- `fnc_symbolPalette` maps an affiliation and a palette to a colour.
- `fnc_symbolFrame` maps an affiliation and a dimension to the frame polylines.
- `fnc_symbolIcon` maps an icon id to a list of vector primitives.
- `fnc_symbolResolve` maps the inputs to one symbol specification.
- `fnc_symbolDrawPlan` turns a specification into an ordered primitive list.

`fnc_symbolResolve` returns `[affiliation, frameShape, dimension, colourRGBA,
iconId, echelon]`. The side argument is carried, not read, because the
affiliation is already resolved. `fnc_symbolDrawPlan` calls the pure frame and
icon kernels only, so it reads no engine draw command.

The category table `aee_optics_symbologyTables` is generated from
`data/symbology/symbology_tables.json`. The generator
`tools/validation/gen_symbology_tables.py` writes the SQF, and the validator
`tools/validation/validate_symbology.py` checks it. The table maps an engine
marker type or a vehicle class to a class category. A marker type uses an exact
match, then the longest prefix, then the suffix.

Three engine adapters carry the engine reads. `fnc_symbologyMarkerCategory`
reads `markerType`. `fnc_symbologyUnitCategory` reads `typeOf` and the vehicle
class. `fnc_symbologyAffiliation` reads `getMarkerColor` and maps the colour
class to an affiliation.

### The draw plan

`fnc_symbolDrawPlan` orders the primitives. The frame outline comes first, the
inner glyph next, the echelon marks third and the label anchors last. Each
primitive is `[kind, points, colourHint]`. The colourHint is `frame` or `icon`.
The draw layer applies the RGBA from the specification, so geometry and colour
stay separate. A label anchor is a one-point poly, so the draw layer branches on
the point count.

### The hide-and-redraw mechanism

The map layer hooks the map control at `findDisplay 12 displayCtrl 51` with
`ctrlAddEventHandler ["Draw", ...]`. It hides the engine mission markers
locally. It walks `allMapMarkers`, records the original `markerAlpha` and calls
`setMarkerAlphaLocal 0`. It restores the recorded alpha when the map closes.
It calls no global marker command, so a multiplayer session is not disturbed.

The layer suppresses the engine unit indicators with
`disableMapIndicators [true, true, true, true]` where the difficulty exposes
extended map content. The suppression is local. The map geometry converts
through `ctrlMapWorldToScreen` and `ctrlMapScreenToWorld`, then draws with
`drawPolygon`, `drawLine`, `drawEllipse` and `drawIcon`. The label draws with an
empty texture, so no image is vendored.

The world layer is a `Draw3D` handler. It draws the frame and the glyph with
`drawLine3D` and the label with `drawIcon3D`. It rebuilds the unit list at most
once a second and draws out to a set range.

### The font

The layer uses the Rajdhani family for the labels and the B612 Mono family for
the monospaced readout. Both are SIL Open Font License 1.1. The two `OFL.txt`
files and the three TTF files are committed under
`addons/optics/data/fonts/`.

The engine loads converted `.fxy` glyph indices and `.paa` glyph atlases. It
does not load a raw TTF. The conversion has two steps and the record states them
honestly.

1. The TTF to `.fxy` and `.tga` step uses the Arma 3 Tools FontToTGA. This step
   needs Windows and is an operator step.
2. The `.tga` to `.paa` step runs in the repository with
   `hemtt utils paa convert`. This step runs on Linux and in CI.

Until the operator runs step 1, the `.fxy` and `.paa` files do not exist. The
engine then falls back to its default font, so the default state is unchanged.
The setting `aee_optics_symbologyFont` gates the label font, with the engine
font as the fallback.

The config adds `CfgFontFamilies` classes `AEEFont` and `AEEFontMono`, and a
`RscMapControl` override with `fontGrid = "AEEFont"`. No runtime command
repoints `fontGrid`, so the override is the only route.

### The per-constant register

Every new numeric is sourced, derived, or marked UNSOURCED.

| Kernel | Constant | Value | Source | Grade |
|---|---|---|---|---|
| palette | friend colour | `[0, 1, 1, 1]` cyan | APP-6(C) Table 1-4 | sourced |
| palette | hostile colour | `[1, 0, 0, 1]` red | APP-6(C) Table 1-4 | sourced |
| palette | neutral colour | `[0, 1, 0, 1]` green | APP-6(C) Table 1-4 | sourced |
| palette | unknown colour | `[1, 1, 0, 1]` yellow | APP-6(C) Table 1-4 | sourced |
| palette | OPFOR swap | friend and hostile | the operator palette choice | derived |
| frame | base shapes | rect, diamond, square, quatrefoil | APP-6(C) frame grammar | sourced |
| frame | dimension modifiers | dome, curve, apex, bar, circle | APP-6(C) dimension grammar | sourced |
| frame | arc sample count | 8 | none | UNSOURCED |
| frame | arc curve | parabola | none | UNSOURCED |
| frame | quatrefoil lobe half-side | 0.5 | unit-box fit | derived |
| frame | friend half-extents | 1 by 0.6 | APP-6(C) frame ratio | derived |
| frame | neutral half-extents | 0.7 by 0.7 | unit-box fit | derived |
| icon | glyph coordinates | about 20 classes | none | UNSOURCED |
| resolve | dimension per category | land, air, sea, subsurface, installation | APP-6(C) dimension grammar | derived |
| draw-plan | echelon mark row | 0.8 | above the frame | derived |
| draw-plan | echelon mark shapes | dot, bar, X | APP-6(C) Table 3-7 | derived |
| draw-plan | label anchors | `[0, 1]` and `[0, -1]` | APP-6(C) Table 3-2 | derived |
| world | draw range | a set metre range | none | UNSOURCED |
| world | rebuild interval | 1 second | none | UNSOURCED |
| map | hidden marker alpha | 0 | engine local hide | derived |

The Table 1-4 colours and the frame grammar are sourced. The glyph coordinates
are UNSOURCED vector approximations. Each UNSOURCED shape is marked in its
kernel header.

## Alternatives rejected

- A vendored texture library. The three studied Workshop marker mods do not
  permit reuse, and a `.paa` set is large. AEE draws its own vector glyphs
  instead.
- A new PBO. The layer lives in `addons/optics`, so no new addon and no new load
  order is needed.
- The engine unit icons. The engine 3D unit icon has no per-object script
  surface, so it cannot be removed. The world layer draws over it and states the
  ceiling.
- A proprietary font. The two chosen families are SIL Open Font License 1.1, so
  the licence permits the conversion and the redistribution.
- An invented glyph coordinate. A stated ceiling is honest and an invented value
  is not.

## Consequences and ceiling

- **The engine 3D unit icons remain.** The engine 3D unit icon cannot be
  suppressed. No script command and no config field removes it. The world layer
  draws its symbol over the engine icon and states this ceiling.
- **The glyph set is curated.** APP-6 holds thousands of function glyphs. AEE
  draws about twenty vector classes and states the ceiling. Anything outside the
  set falls back to the engine icon texture in the map layer.
- **The frame arcs are derived.** The standard gives no curve equation. The dome
  and the curved bottom edge are parabola approximations, marked UNSOURCED.
- **The marker suppression is partial.** The local hide covers the mission
  markers only. The unit indicator suppression needs the difficulty to expose
  extended map content. The engine 3D icon stays in every case.
- **The font needs an operator step.** The TTF to `.fxy` and `.tga` conversion
  needs the Windows FontToTGA tool. The `.tga` to `.paa` step runs in the
  repository. Until the operator runs step 1, the engine font is used.
- **The visual result is operator-only.** A headless server has no local player.
  The Docker probe P111 tests the pure kernels with fixtures. The visible map,
  the visible world symbol and the visible font each need one operator run.
