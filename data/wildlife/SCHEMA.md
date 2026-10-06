# Wildlife ecology corpus schema

The wildlife ecology corpus is the only home for a real species group, its
behaviour rule and its sound identity. A loader rejects any field without a
source grade. The generated runtime projection reads the corpus, not a game
config and not a hand-set per-map table.

This document defines the contract. It holds no species data. It ships no
group and no media path. The source registry holds the documents. The corpus
files hold the entries.

Cite the governing rules in a change record: JSP 945 for configuration
management and Def Stan 05-138 for cyber security.

## 1. The layers

The corpus has four layers. Keep them apart.

1. Species group. A real taxonomic group with its behaviour and habitat rule.
2. Asset map. The sound groups and the vanilla fauna classes, with an
   identity grade.
3. Source record. The held document with its tier, type and locator.
4. Generated runtime projection. The SQF corpus and asset map built from
   layers 1 to 3.

A layer never borrows a value from another layer.

## 2. The files

| File | Role |
|---|---|
| `data/wildlife/SCHEMA.md` | This contract. |
| `data/wildlife/sources.json` | The source registry. A top-level array. |
| `data/wildlife/ecology.json` | The species-group corpus. |
| `data/wildlife/asset_map.json` | The sound and fauna identity map. |

The two data files follow the `data/device/catalogue/` shape: `retrieved`,
`note`, `sources` and an entry list. `sources` is a retired compatibility
field. It stays an empty array. Every source is registered in
`sources.json`. The entry list is `families` in `ecology.json` and
`sound_groups` plus `faunal_groups` in `asset_map.json`.

## 3. The source registry

Write the registry at `data/wildlife/sources.json`. It is a top-level array.
One entry is one held document.

Required fields are `source_id`, `tier`, `type` and `title`. Expected fields
are `edition`, `identifier`, `locator`, `published`, `retrieved`, `url` and
`note`.

- `source_id`: stable snake_case key. One id per document.
- `tier`: the document tier. Section 4 gives the order.
- `type`: `reference`, `measurement`, `compilation` or `primary`.

## 4. Source tiers and order

The order is UK MOD first, NATO second, US DOD last. This corpus holds no
military document, so the tiers rank reference quality only.

1. Tier 1: an issued standard or specification.
2. Tier 2: a manual or a technical manual.
3. Tier 3: a reference work, a peer-reviewed measurement or a primary paper.
4. Tier 4: a manufacturer datasheet.
5. Tier 5: a compilation, a community wiki or a repository research note.

A tier 5 entry supports a grade at `R` or weaker only. It never displaces a
tier 1 to tier 4 value.

## 5. The source grades

Every field carries one grade. The allowed set is `S`, `S-lit`, `R` and `U`.

| Grade | Meaning |
|---|---|
| `S` | Sourced and fetched this session. A fetched figure or formula. |
| `S-lit` | Sourced to named literature reached through a fetched page. |
| `R` | Documented in a standard reference database. The exact figure is not fetched. |
| `U` | UNKNOWN or UNSOURCED. No source obtained. A modelling choice. |

A field at grade `U` is a modelling choice, not a published value. It is
listed again in the per-constant register in section 8. No numeric is stated
unless its field is graded, and an `S` or `S-lit` field is the only place a
published figure may appear.

## 6. The species-group entry

Write one group per real taxonomic group at `data/wildlife/ecology.json`. A
family entry holds `family`, `koppen_letters`, `overlay` and `groups`.

| Field | Type | Meaning |
|---|---|---|
| `group_id` | string | Stable snake_case key. Unique in the corpus. |
| `family` | enum | A family or overlay key. Section 7 gives the set. |
| `taxa` | array | The real taxa, for example `["Aves"]`. |
| `activity` | enum | `diurnal`, `nocturnal` or `crepuscular`. |
| `season` | object | `months` (a list of month numbers) and `rule` (text). |
| `temperature_c` | object | `min` and `max` in degrees Celsius. |
| `wind` | object | `limit_ms` and `suppression` (0 to 1). |
| `rain` | object | `limit`, `suppression` (0 to 1) and `triggers` (bool). |
| `gregariousness` | enum | `solitary`, `territorial`, `pair`, `flocking` or `chorus`. |
| `habitat` | object | `foliage`, `surface`, `water`, `structures`, each 0 to 1. |
| `temporal` | object | `bins` (seven weights) and `dolbear` (bool). |
| `sound_group` | string | A key in `asset_map.json`. |
| `field_grades` | object | One grade per field name. Section 5 gives the set. |
| `grade` | enum | The group grade, the weakest field grade. |

The seven temporal bins, in order, are `pre_dawn`, `dawn`, `morning`,
`midday`, `afternoon`, `dusk` and `night`. A weight is 0 to 1.

A `dolbear` true group is a cricket or katydid. Its rate comes from the
Dolbear shortcut only. Section 8 gives the shortcut.

## 7. The family set

Every family key named in `fnc_speciesForBiome.sqf` is present. The set is
`tropical`, `arid`, `temperate`, `cold`, `water` and `settlement`. The first
four are Koppen family keys. `water` and `settlement` are overlays.

## 8. The per-constant register

Every numeric is sourced, derived with its formula, or marked UNSOURCED
here. The register lives in `ecology.json` under `constants`. One entry
carries `name`, `value`, `unit`, `grade` and `note`.

| Constant | Value | Grade | Note |
|---|---|---|---|
| Dolbear shortcut | `T_C = 5 + N8` | S | Dolbear 1897. The only cricket rate source. |
| Dolbear valid band | 5 to 30 C | S | The band the shortcut is accurate in. |
| Family temperature bands | per group | U | A modelled envelope. No published band. |
| Wind limit and suppression | per group | U | A modelled song-suppression rule. |
| Rain limit and suppression | per group | U | A modelled masking rule. |
| Habitat weights | per group | U | A modelled habitat preference. |
| Temporal bin weights | per group | U | A modelled calling shape. |
| Desert cicada cooling point | 39 C | S | Wikipedia, Cicada. |
| Flight-initiation distance, small bird | 8 to 25 m | S-lit | Blumstein 2003, Ydenberg and Dill 1986. |

## 9. The asset map

Write `data/wildlife/asset_map.json` with two entry lists.

`sound_groups` maps a sound-group key to the vanilla media and the vanilla
fauna classes. A media entry carries `path` for a raw `.wss` file or
`cfg_sfx` for a CfgSFX class. The `identity` is `CONFIRMED`, `UNCONFIRMED`
or `UNKNOWN`.

`faunal_groups` maps a family to the confirmed vanilla `CfgVehicles Animals`
classes, transcribed from `addons/wildlife/data/species_table.sqf`.

Rules:

- A media path begins with `a3\`. No path begins with `x\` or `z\`.
- A CfgSFX class is `Owl` or `Sound_Stream`, the two the manifest confirms.
- `sarance` and `chicken_grill` are UNKNOWN. They are never given a species.
- `hen`, `dog`, `seagul_1` and `sheep` are UNCONFIRMED name-only. They are
  never given a species.
- A sound group with no pinned media carries an empty `media` list and an
  `anchor` note. No path is invented.

## 10. The generated runtime projection

The generator `tools/validation/gen_wildlife_ecology.py` writes two SQF
files.

- `addons/wildlife/data/ecology_corpus.sqf`: one row per species group.
- `addons/wildlife/data/asset_map.sqf`: one row per sound group and per
  faunal group.

The row shape is documented in each generated file header. The order is by
id, so the output is stable. The `--check` mode writes nothing and returns 1
when a generated file is stale.
