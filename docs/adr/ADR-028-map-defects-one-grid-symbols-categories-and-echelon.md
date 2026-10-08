# ADR-028: The four map defects - one grid, every marker family, categories, the echelon above

Status: Accepted

## Context

The operator reported four map defects on a clean RPT, so they are behavioural:
the engine numeric grid draws beside the AEE MGRS grid; not every engine marker
family renders an AEE symbol; the AEE markers sit in one flat `CfgMarkerClasses`
list; and the echelon overlay does not render above the unit frame.

## Decision

### Defect 1 - exactly one grid

AEE suppresses the engine numeric grid and keeps its MGRS grid. The engine grid
is drawn from `CfgWorlds >> <world> >> Grid` (the per-world step, offset and
digit format) and `RscMapControl` (the presentation). `CfgWorlds` can only
relabel, respace and shift the grid, so the presentation is the only lever: the
lines are `colorGrid[]` and `colorGridMap[]` (alpha 0), the numbers are
`sizeExGrid` (0). The fields are set on `RscMapControl` and, because they are
separate override targets, on `RscDisplayStrategicMap >> controlsBackground >>
Map` and on the Eden `ctrlMap`. The engine grid is numeric and cannot carry
MGRS, so this route is taken over driving the engine grid. Source: MIL-STD-2525D
and the Arma engine default `RscMapControl`.

### Defect 2 - every engine marker family

`tools/gen_symbology_catalogue.py` re-declares each engine marker class with an
AEE `.paa`. The affiliation families (`b_`, `o_`, `n_`, `c_`) resolve through
the catalogue; the other families are named to the AEE symbol they mean: the
header and military tactical graphics (`hd_`, `mil_`) to the generic dot or the
matching mission task, `Contact_` to the dot (artillery to the artillery glyph),
`GroundSupport_` to the aircraft or artillery glyph, `group_0`..`group_11` to
the echelon ladder, `respawn_` to the unknown set, `waypoint` to the dot.

Recorded ceilings, not oversights:

- `flag_` (43 national flags): a national flag is not an APP-6 affiliation
  symbol. Re-pointing it to a unit symbol would misrepresent it.
- `loc_` (85 location icons): the location icons are drawn by `CfgLocationTypes`,
  which AEE already re-textures from the DGIWG register (ADR-026). The `loc_`
  picker entries point at that same surface.
- `Empty`, `EmptyIcon`: these are the invisible markers. Re-pointing `Empty`
  would show a symbol where the engine draws nothing.
- `Flag`, `KIA`: the base flag class and the death marker carry no icon.

### Defect 3 - categories and subcategories

The engine marker picker is a flat list of `CfgMarkerClasses`, so AEE carries the
hierarchy in the class name and the displayName: the category is the
affiliation, the subcategory is the battle dimension, and the three modifier
groups are their own categories. `tools/symbology_categories.py` is the single
source; the four generators emit the `markerClass` per marker; `config.cpp`
declares the matching classes; `tools/tests/test_symbology.py` pins them
together.

### Defect 4 - the echelon above the frame

The engine STRETCHES a marker texture into its box and does not keep the texture
aspect (feedback T170754). The echelon overlay is 64 x 128, so a square marker
box squashes it and the ticks land inside the frame. The fix is a 1:2 marker
box, computed by the pure kernel `fnc_symbologyEchelonSize` from the frame's
half-width so the two boxes align. The 3D `drawIcon3D` already used width 1.5
and height 3.0 (1:2). APP-6 places the echelon above the frame (MIL-STD-2525D
field B, figure 12; APP-6(C) figure 3-3) - the two standards disagree on whether
it sits inside the frame (APP-6(C)) or outside it (MIL-STD-2525D); AEE follows
2525D and places it above.

## Ceilings

- The strength and status amplifiers are not drawn. APP-6(C) drives the strength
  from a unit-strength datum and the status from a readiness datum. The engine
  exposes neither, so AEE draws neither and invents no signal (ADR-025).
- The engine grid is removed on every `RscMapControl` surface, but the AEE MGRS
  grid is drawn on the main map display only. The GPS carries the MGRS readout
  (`fnc_gpsUpdate`); the minimap and briefing carry no grid.
