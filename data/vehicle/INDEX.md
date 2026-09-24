# Vehicle corpus index

The vehicle corpus gives every supported AEE ground class a source-backed
real-world counterpart. The corpus holds the only real vehicle values. The
game config is identity evidence. The generated runtime lookup returns no
result when the class or a field is unknown.

Read `data/vehicle/SCHEMA.md` for the catalogue contract, the class map,
the value object, the source tiers, the grades and the fail-closed rules.

## 1. Layers

The corpus has five layers. Keep them apart. Each layer has one owner and
one output.

### 1.1 Class identity

Class identity is the AEE game class and its supported class token. The
inventory tool derives the tokens from the addon code. It collects every
`isKindOf` literal and every token in a vehicle class table. The tool
writes `data/vehicle/classes.json`, sorted and deterministic.

Class identity is evidence of what AEE supports. The game config and a
class token are identity or model-geometry signals only. They are never a
real-world value. A game class name is not a maker, a model or a variant.

### 1.2 Real-world catalogue entry

A real-world catalogue entry is one real maker, model and variant. One
entry holds one variant. The entry carries `catalogue_id`, the canonical
name, the maker, the model, the variant, `variant_id`, the vehicle type,
the class token, the country, the era, the aliases, the keywords, the
`runtime_ready` flag and the value objects.

Write one capture file for each held source at
`data/vehicle/catalogue/<source_id>.json`. The field list is in
`data/vehicle/SCHEMA.md` section 6.

### 1.3 Class-to-catalogue map

The class-to-catalogue map is the recorded link from one game class to
one catalogue entry. The map is `data/vehicle/class_map.json`.

A real-world source that names the vehicle grades the link `documented`.
An engine class table or engine config can bind a class only at grade
`claimed`, and the evidence must name the concrete token or kind. A
category guess is not a mapping. A mapping with no source is a lead. It
stays in the gap artefact.

### 1.4 Source record

A source record is one held document. It carries the title, the edition,
the locator, the retrieval date, the tier, the type and the digest of the
held bytes. The registry is `data/vehicle/sources.json`. The held
documents live under `data/vehicle/sources/`.

A value names its source by id. A value whose source is absent from the
registry is an error. A compiled page is never marked primary.

### 1.5 Generated runtime projection

The generated runtime projection is an SQF matcher. The generator
`tools/validation/gen_vehicle_data.py` writes
`addons/mobility/functions/fnc_getVehicleData.sqf`. The file is never
edited by hand. The header names the generator and states the unit of
every column.

The matcher runs a five-layer ladder: exact class, alias, keyword,
inheritance, closest. The result is a flat array with `catalogue_id`,
`variant_id`, `vehicle_type`, `confidence`, `matched_by`,
`source_record_id` and `valueRow`. The projection reads no config and no
registry at runtime. It returns `[]` when the class is unknown, when the
match is ambiguous and when the variant is ambiguous.

A row is emitted for every entry whose identity is complete. A runtime
field resolves to a held value, a named derivation or a labelled absent
zero. A labelled weak value beats a silent zero: a missing field is a zero
for a number or an empty string for a word, never a refusal of the record.

## 2. Pipeline

The stages run in this order. Each stage writes one output.

1. Derive the class inventory into `data/vehicle/classes.json`.
2. Write the sources into `data/vehicle/sources.json`.
3. Write the catalogue entries into `data/vehicle/catalogue/`.
4. Write the class-to-catalogue map into `data/vehicle/class_map.json`.
5. Validate the corpus with `tools/validation/validate_vehicle_data.py`.
6. Generate the coverage and gap artefacts with
   `tools/validation/gen_vehicle_coverage.py`.
7. Generate the projection with `tools/validation/gen_vehicle_data.py`.

The validator is the gate. It rejects an unsourced value, a config-derived
value, a missing unit and a missing state. It rejects a catalogue entry
with no runtime field that resolves from a held value or a named
derivation. It requires a derived value to name its formula. It permits an
engine class table or config as a class-map source only at grade `claimed`
with evidence that names the concrete token. It exits 1 on an error.

## 3. Files

| Path | Layer | Role |
|---|---|---|
| `data/vehicle/SCHEMA.md` | contract | The catalogue, map and source contract. |
| `data/vehicle/INDEX.md` | contract | This layer model. |
| `data/vehicle/classes.json` | identity | Derived supported tokens. |
| `data/vehicle/sources.json` | source | The held document registry. |
| `data/vehicle/sources/` | source | The held bytes. |
| `data/vehicle/catalogue/` | entry | One capture file per held source. |
| `data/vehicle/class_map.json` | map | The class-to-catalogue links. |
| `data/vehicle/fixtures/` | entry | Deliberate invalid test fixtures. Never production entries. |
| `data/vehicle/coverage.json` | coverage | A state for every token. |
| `data/vehicle/conflicts.json` | entry | Kept disagreements. |
| `data/vehicle/COVERAGE_AUDIT.md` | coverage | Generated per-token coverage. |
| `data/vehicle/SOURCE_GAPS.md` | coverage | Generated per-entry missing fields. |
| `data/vehicle/CLASS_MAPPING_GAPS.md` | coverage | Generated unmapped classes and tokens. |
| `data/vehicle/RESEARCH_GAPS.md` | entry | The hand-written lead register. |

The `data/vehicle/fixtures/` layer holds a deliberate invalid pilot
fixture. It is a negative-test and audit artefact. The validator must
reject it. It is outside the catalogue path, so the production corpus
holds no invalid entry.

The layer also holds `fixtures/sources.json`. That file keeps the former
fixture source entries out of the production registry. The production
registry holds real held documents only.

The prior `data/vehicle/records/` capture path is replaced by the
`catalogue/` path in this revision. The `records/` directory holds no
production file.

## 4. Coverage table

The coverage guard gives every token in `classes.json` one state. The
states are `recorded`, `lead`, `no_source` and `excluded_non_ground`. A
token never leaves the inventory in silence. A `recorded` token has an
emitted runtime row and a class-map binding for the token. The audit
reports both the recorded count and the emitted runtime row count.

The table below is a stub. The coverage guard fills the rows. The stub
names no class.

| Token | Kind | Ground | State | Entry | Reason |
|---|---|---|---|---|---|
| | | | | | |

## 5. Fail-closed summary

The matcher returns no result in these cases. They are an unknown class,
an identity-incomplete entry, an ambiguous variant and a tie at one match
layer. The runtime projection returns `[]` in every case. It never returns
a default.

A missing field is not a no-result case. A labelled weak value beats a
silent zero: the row states a graded value for every runtime field. A
field with no held value and no derivation is a zero for a number or an
empty string for a word, graded `absent`. The grade and the derivation
basis are reported in the coverage and source-gap artefacts.

The required runtime fields are the seven NRMM inputs of the vehicle
type. `data/vehicle/SCHEMA.md` section 10 lists the wheeled set and the
tracked set.

## 6. Status

This document and the schema define the contract. The inventory, the
source registry, the catalogue, the class map, the coverage guard and the
projection exist. The corpus holds four held tier-2 catalogue entries: two
wheeled, one tracked and one wheeled MRAP. Every entry has a complete
identity, so each one emits a runtime row. No entry is runtime-ready: each
one still carries at least one absent runtime field.

`data/vehicle/class_map.json` holds four `claimed` engine class-table
bindings, one per entry, to the AEE tokens `Car`, `Truck`, `Tracked_APC`
and `MRAP`. The coverage guard reports four recorded tokens and four
emitted runtime rows. A real-world mapping source is still missing, so the
bindings stay `claimed`.

The governing rules are JSP 945 for configuration management and
Def Stan 05-138 for cyber security. The source order is UK MOD first,
NATO second, US DOD last, then a manufacturer and then a compilation.
