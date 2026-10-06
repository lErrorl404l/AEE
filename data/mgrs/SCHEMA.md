# MGRS lettering and world anchor schema

The MGRS layer holds two things: the fixed lettering of the Military Grid
Reference System, and one geographic anchor per shipped world. The lettering
is the same for every map. The anchor is the map-specific geographic box.

This document defines the contract. It holds no letter and no anchor value.
The sources hold the documents. The data files hold the values. The generated
runtime projection holds what the kernels read.

Cite the governing rules in a change record: DMA TM 8358.1 and DMA TM 8358.2
for the grid, and the NGA MGRS guidance (Modified February 2009) for the
lettering and the precision. Configuration management is JSP 945.

## 1. The layers

Four layers. Keep them apart.

1. Source registry. The held documents, in `sources.json`.
2. Letter tables. The band letters, the column sets, the row letters, the AA
   offset, the zone strings and the digits, in `mgrs_tables.json`.
3. World anchors. The raw CfgWorlds values and the resolved anchor per world,
   in `geo_sources.json`.
4. Generated runtime projection. `addons/core/data/mgrs_tables.sqf`, read by
   the kernels as `aee_core_mgrsTables`.

A layer never borrows a value from another layer.

## 2. The files

| File | Role |
|---|---|
| `data/mgrs/SCHEMA.md` | This contract. |
| `data/mgrs/sources.json` | The source registry. A top-level array. |
| `data/mgrs/mgrs_tables.json` | The letter tables. |
| `data/mgrs/geo_sources.json` | The world list and the resolved anchors. |
| `addons/core/data/mgrs_tables.sqf` | The generated runtime projection. |

The generator `tools/validation/gen_mgrs_tables.py` writes the projection and
resolves the anchors. Do not edit either generated output by hand.

## 3. The source registry

Write the registry at `data/mgrs/sources.json`. It is a top-level array. One
entry is one held document. Required fields are `source_id`, `tier`, `type`
and `title`. Expected fields are `edition`, `identifier`, `locator`,
`published`, `retrieved`, `url` and `note`.

- `source_id`: stable snake_case key. One id per document.
- `tier`: 1 for a primary or authoritative document, 3 for a secondary.
- `type`: `primary`, `reference`, `measurement` or `compilation`.

Every source id named by `mgrs_tables.json` must be registered here.

## 4. The letter tables

Write the tables at `data/mgrs/mgrs_tables.json`. The `tables` object holds six
components, each with a `grade` and a `note`:

| Component | Content | Rule |
|---|---|---|
| `band_letters` | 20 letters | C to X, omitting I and O. 80 S start, 8 deg each, X is 12 deg. |
| `column_sets` | 3 sets of 8 | Zone set 1 A-H, set 2 J-R (omit O), set 3 S-Z. Index `(zone - 1) mod 3`. |
| `row_letters` | 20 letters | A to V, omitting I and O. Index `(northing / 100000) mod 20`. |
| `even_zone_row_offset` | one number | 5. The AA scheme: odd zones start at A, even zones at F. |
| `zone_strings` | 60 strings | "01" to "60". Leading zeros. |
| `digit_characters` | 10 strings | "0" to "9". |

The datum is WGS84 and the scheme is AA. The older AL scheme (odd L, even R)
is for local datums and is not used here. The validator refuses any letter
outside these sets, so a letter can never be invented.

## 5. The world anchors

Write the world list at `data/mgrs/geo_sources.json`. Each world records the
raw CfgWorlds values `mapSize`, `mapZone`, `mapArea`, `latitude` and
`longitude`, and the resolved `anchor` and `anchor_source`.

`mapArea` is read in the authoritative BIS order `[lonWest, latSouth, lonEast,
latNorth]`. The anchor is the 9-element schema:

```
[latCentre, lonCentre, zone, mapSize, lonWest, latSouth, lonEast, latNorth,
 sourceToken]
```

`sourceToken` is `mapArea` when the box is present, non-degenerate and inside
valid bounds, else `cfgworlds`. The latitude key is negated because BIS stores
it inverted. The generator resolves the anchor with the same rule as the pure
builder `aee_core_fnc_buildGeoAnchor`, and the validator proves the two agree
by running the shipped builder through `tools/tests/sqf_lite.py`.

## 6. The invariants

The validator `tools/validation/validate_mgrs.py` enforces:

1. Every table component is present, typed, and carries a grade.
2. The letters are exactly the published sets; I and O are never used.
3. The zone strings are "01" to "60" and the digits are "0" to "9".
4. Every world in `geo_sources.json` has a 9-element anchor row.
5. Every anchor equals the shipped pure builder.
6. Every source id the tables name is registered.
