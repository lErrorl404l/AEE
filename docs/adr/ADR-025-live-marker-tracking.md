# ADR-025: Live marker tracking - death, echelon, dimension and the engine ceiling

Status: Accepted

## Context

ADR-024 registers the AEE APP-6(C) symbol set as real engine map markers, and
ADR-025 adds the taxonomy, the mission-task graphics, the amplifier modifiers
and the echelon overlays. Both records leave the runtime symbol derived from
one engine read, and both state a ceiling for the surfaces the engine does not
expose.

The map layer `fnc_symbologyMarkersApply` and the 3D layer
`fnc_symbologyWorldDraw` then draw one symbol per unit. Four gaps remained:

1. a dead unit kept its marker, because the unit list carried no `alive` test;
2. the echelon overlay classes `AEE_Ech_<Name>` existed in the config, but no
   runtime code selected them;
3. the resolver passed a hardcoded `"land"` dimension to the type kernel, so an
   air, sea or installation unit drew a land frame;
4. the symbol was keyed by `netId` and derived from `typeOf` every scan, so a
   unit that mounts or dismounts did not change symbol, and no code folded a
   mounted group into one mechanised symbol.

This record states the decision for each gap and the engine ceiling that
bounds it.

## Decision

### Death clears the marker and revive restores it

The unit list in `fnc_symbologyMarkersApply` collects the player only when
`alive _player`, and each `allUnits` entry only when `alive _x` and within
range. A dead unit therefore produces no entry, and the existing cleanup loop
deletes its `AEE_UNIT_<netId>` marker and its `AEE_ECH_<netId>` companion. The
next scan re-creates both when the unit revives. The 3D worker keeps its own
`alive _unit` test, so its behaviour for the player is unchanged.

### The echelon is derived from group size and layered

`fnc_symbologyEchelon` is a pure kernel that maps a group size to an echelon
token. `fnc_symbologyUnitEchelon` is the adapter that reads
`count units (group _unit)`. The bands are AEE derivation, UNSOURCED: the
standard gives a nominal strength for each echelon, not a count function, so
the band edges are AEE own and are marked as such. The bands are monotone: a
larger group never yields a lower echelon.

| Ground size | Echelon token |
|---|---|
| 1 | team |
| 2 to 6 | squad |
| 7 to 13 | section |
| 14 to 40 | platoon |
| 41 to 150 | company |
| 151 to 500 | battalion |
| 501 to 2000 | regiment |
| 2001 to 6000 | brigade |
| 6001 to 15000 | division |
| 15001 to 60000 | corps |
| 60001 to 120000 | army |
| 120001 to 300000 | army_group |
| over 300000 | region |

`fnc_symbologyEchelonMarker` maps a token to the CfgMarkers class
`AEE_Ech_<Name>`. The overlay is a 64 x 128 texture with the ticks in the top
band. The map layer creates the frame marker first and the echelon companion
`AEE_ECH_<netId>` second, at the same position, so the overlay draws on top.
The 3D worker draws a second `drawIcon3D` for the same overlay texture at the
same origin, width 1.5 and height 3.0, in the same colour and with no text.
Both layers track the companions in `QGVAR(symbologyUnitEchelonMarkers)` and
`fnc_symbologyMarkersRestore` deletes them and resets the cache.

### The dimension is derived and rendered by a dimension-correct texture

`fnc_symbologyDimension` is a pure kernel that maps a class category to its
battle dimension, using a new generated section six of
`aee_symbology_symbologyTables`. `fnc_symbologyUnitDimension` is the adapter that
carries a unit's category through it. `fnc_symbolResolve` gains a sixth
argument `_dimension` and passes it to `fnc_symbologyMarkerType` in place of
the hardcoded `"land"`.

`fnc_symbologyMarkerType` still returns `AEE_<family>_<glyph>`. The type name
does not select the frame: the CfgMarkers class texture does. The root cause
of the land frame on a non-land unit is therefore the stale vanilla icon path
on the `AEE_<family>_<glyph>` class. The decision is to re-point the affected
simple classes at dimension-correct catalogue textures that already exist
under `data/markers`:

| Glyph | Dimension | Friendly | Hostile | Neutral |
|---|---|---|---|---|
| plane | air | `AEE_FA_Friendly_Unit_Aviation_Fixed_Win.paa` | `AEE_HA_Hostile_Unit_Aviation_Fixed_Wing.paa` | `AEE_NA_Neutral_Unit_Aviation_Fixed_Wing.paa` |
| uav | air | `AEE_FA_Friendly_Unit_Unmanned_Aerial_Ve.paa` | `AEE_HA_Hostile_Unit_Unmanned_Aerial_Veh.paa` | `AEE_NA_Neutral_Unit_Unmanned_Aerial_Veh.paa` |
| air | air | `AEE_FA_APP_6_Army_Aviation.paa` | `AEE_HA_Hostile_Unit_Aviation.paa` | `AEE_NA_Neutral_Unit_Aviation.paa` |
| naval | sea | `AEE_FS_Friendly_Unit_Naval.paa` | `AEE_HS_Hostile_Unit_Naval.paa` | `AEE_NS_Neutral_Unit_Naval.paa` |
| installation | installation | `AEE_FI_Installation.paa` | `AEE_HI_Installation.paa` | `AEE_NI_Installation.paa` |

The `u_*` classes are already produced with correct frames and are not
re-pointed. Land glyphs are not re-pointed. The mission-marker conversion and
`fnc_hudMarkers` are not unit-backed, so they keep the default `"land"`.

### Role, join and leave

A unit marker is keyed by `netId`, and its symbol is derived from `typeOf`
every scan. A unit that mounts or dismounts does not change symbol: it keeps
the passenger or infantry class from its own `CfgVehicles` data, and the group
is never queried for a vehicle. The engine exposes no group-level mounted
state, so AEE does not fold a mounted group into one mechanised symbol. This
is a recorded ceiling, not an oversight.

The engine does allow `vehicle _unit` and `typeOf vehicle _unit` per unit, and
each member has its own `netId`. Joining or leaving a group changes only
`group _unit`, which the marker key ignores. A per-unit mount preference was
considered and rejected for this change: the clean place for it is the shared
category adapter, and that would change the symbol for every mounted unit,
map and world, with no standard rule that says an APC crew reads as an armour
symbol. The ceiling is recorded and the code is left as it is.

### Strength and status

APP-6(C) strength and status amplifiers are text or overlay modifiers driven
by a strength and a readiness datum. The engine exposes no unit-strength, no
readiness and no status datum. AEE draws no strength or status modifier, and
the ceiling is recorded. No signal is invented.

## The engine ceiling

| Surface | Status | Mechanism or absence |
|---|---|---|
| Unit death | tracked | `alive` gates the unit list; the cleanup deletes the marker and the next scan restores it |
| Group size | tracked | `count units (group _unit)`; the band edges are AEE derivation, UNSOURCED |
| Group type or composition | ceiling | no group-type command exists; the group is never queried for a vehicle |
| Group-vehicle query | ceiling | no group-level mounted state; `vehicle _unit` is per unit only |
| Echelon construct | ceiling | the engine has no echelon datum; the echelon is derived from the group count |
| Class category to dimension | tracked | the generated section six plus `fnc_symbologyDimension` |
| Strength signal | ceiling | no unit-strength datum |
| Readiness or status signal | ceiling | no readiness and no status datum |

## Consequences

- Death clears the unit marker and its echelon companion, and revive restores
  both. The map no longer shows a dead unit as live.
- The echelon overlay appears above the frame on the map and in the 3D view,
  derived from the group count. The bands are derived and UNSOURCED.
- Air, sea and installation units draw a dimension-correct frame, because the
  simple class points at a dimension-correct texture. The type name is
  unchanged, so existing tests that pin `AEE_<family>_<glyph>` still hold.
- A mounted group is not folded into one mechanised symbol. The ceiling is
  recorded, and a per-unit mount preference is available to a later change.
- No strength or status modifier is drawn. The ceiling is recorded.
- The echelon companion doubles the unit marker count. Each pass deletes the
  companions that left the range, and restore clears the cache on map close.
