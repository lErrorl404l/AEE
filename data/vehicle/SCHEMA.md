# Vehicle corpus source schema

The vehicle corpus is the only home for a real vehicle value. Every value
carries a unit, a source, a locator, a state and a grade. A validator
rejects any value without them. The generated runtime projection reads the
corpus, not a game config.

This document defines the contract. It holds no vehicle data. It ships no
catalogue entry and no class map. The source registry holds the documents.
The catalogue holds the entries. The class map holds the links. The layer
model is in `data/vehicle/INDEX.md`.

Cite the governing rules in a change record: JSP 945 for configuration
management, Def Stan 05-138 for cyber security, and the MOD-first source
order in this document.

## 1. The five layers

The corpus has five layers. Keep them apart.

1. Class identity. The AEE game class and its supported class token.
2. Real-world catalogue entry. The real maker, model and variant, with
   aliases, keywords and per-field sources.
3. Class-to-catalogue map. The recorded link from one game class to one
   catalogue entry, with its own mapping source.
4. Source record. The held document with its digest, tier, locator and
   retrieval date.
5. Generated runtime projection. The SQF matcher built from layers 2 and
   3. It does no runtime source lookup.

A layer never borrows a value from another layer.

The game config and a class token are identity or model-geometry signals
only. They are never a real-world value. A config mass, `getMass`,
`enginePower` and `maxSpeed` are engine values. A class token names what
AEE supports. It does not name a maker, a model or a variant.

No category guess may create a class map. A token that names a category
only is a lead. Section 7 gives the rule.

## 2. The source registry

Write the registry at `data/vehicle/sources.json`. It is a top-level
array. One entry is one held document.

Required fields are `source_id`, `tier`, `type`, `title`, `identifier`
and `retrieved`. Expected fields are `edition`, `locator`, `published`,
`url`, `archive_ref`, `licence`, `primary_held`, `sha256` and `note`.

- `source_id`: stable snake_case key. One id per document.
- `sha256`: the digest of the held bytes under `data/vehicle/sources/`.
- `primary_held`: true only when the primary document is held. A
  secondary copy is never marked primary.

## 3. Source tiers and order

The order is UK MOD first, NATO second, US DOD last. A later tier never
displaces an earlier tier for the same entity and field.

1. Tier 1: an issued standard or specification. UK Def Stan and JSP
   first, then NATO STANAG and AQAP, then a US DOD standard last.
2. Tier 2: a military manual or a technical manual.
3. Tier 3: a reference work, for example a tyre data book.
4. Tier 4: a manufacturer datasheet or product page.
5. Tier 5: a compilation, for example a wiki. Last resort only.

A tier 5 entry is allowed at grade `claimed` only. It is counted in the
build output. It never displaces a tier 1 to tier 4 value. Prefer a
primary source. Reach for a compilation only when nothing stronger
exists. A compilation is never a primary source.

## 4. Source types and hard rules

A source type is a real-world type or an engine type. The real-world
types are `standard`, `manual`, `measurement`, `manufacturer` and
`compilation`. The engine types are `engine_geometry`, `engine_config`
and `class_table`.

The hard rules are these.

1. `engine_config` and `class_table` are FORBIDDEN as an entry source for
   a numeric or categorical value. They are allowed for an identity field
   only. A config mass, `enginePower`, `maxSpeed` and a class table are
   engine values, not real-world values.
2. `engine_geometry` is allowed only for documented model geometry. The
   one permitted quantity is `tyre_diameter_mm`, at grade `derived`, with
   `formula` set to `2 * dist(wheel axis, boundary)`. The wheel count is
   the number of declared wheel stations, at grade `documented`.
3. `engine_config` and `class_table` never displace a real-world source.
4. A game config field gives no operating weight, no tyre width in
   millimetres and no ground clearance. Get those figures from a vehicle
   manual or a tyre record.

The engine evidence is recorded in
`docs/wiki/research/soil-strength-nrmm.md`. Read it before any engine
field enters a record.

## 5. The value object

Every value field is an object with these six keys. A value without a
unit, a source, a locator, a state or a grade is not usable.

```json
{
  "value": "<value>",
  "unit": "<unit>",
  "source": "<source_id>",
  "locator": "<locator>",
  "state": "<state>",
  "grade": "<grade>"
}
```

- `value`: the published number or the published word. A number keeps its
  published precision. A word names one allowed term for an enum field.
- `unit`: an exact string from the unit vocabulary in section 9. It must
  agree with the field unit. A missing unit is an error.
- `source`: the `source_id` of the held document. The id must exist in
  `data/vehicle/sources.json`.
- `locator`: the page, table or row that carries the value. It is precise
  enough to find the value again.
- `state`: the configuration the value belongs to, for example an
  operating weight with full fuel. A value without its state is not
  usable. A field with one configuration states `as published`.
- `grade`: one of the grades in section 8. The grade must agree with the
  source tier and type.

A placeholder in angle brackets is not data. Replace every placeholder
with a sourced value.

## 6. The catalogue entry

Write one capture file for each held source at
`data/vehicle/catalogue/<source_id>.json`. A capture holds `retrieved`,
`note`, `sources` and `entries`. One entry is one real-world catalogue
entry.

`sources` is a retired compatibility field. It must stay an empty array.
Register every source in `data/vehicle/sources.json`. The validator reads
the registry only and rejects a capture whose `sources` array is not empty.

| Field | Type | Meaning |
|---|---|---|
| `catalogue_id` | string | Stable snake_case canonical id. The primary key. |
| `canonical_name` | string | The one canonical name of the vehicle. |
| `maker` | string | The real maker of the vehicle. |
| `model` | string | The real model name. |
| `variant` | string | The real mark or variant. |
| `variant_id` | string | Stable snake_case key of the modelled variant. |
| `vehicle_type` | enum | One of `wheeled` or `tracked`. |
| `class_token` | string | The supported token from `classes.json`, or empty. |
| `country` | string | The country of origin or service. |
| `era` | string | The service era, for example `modern`. |
| `aliases` | array | Lowercase match strings. |
| `keywords` | array | Lowercase match words. |
| `runtime_ready` | boolean | True when section 10 is satisfied. |
| `values` | object | The value objects, keyed by field name. |

Rules:

- `catalogue_id` is unique in the corpus. `variant_id` is unique in the
  corpus.
- `aliases` and `keywords` are lowercase. The runtime normaliser keeps
  `[a-z0-9]` only, as `fnc_getWeaponData.sqf` does.
- An alias shared by two catalogue entries is dropped from the matcher
  index, as the cartridge generator drops a shared cartridge alias.
- `vehicle_type` selects the required set in section 10.
- Every value carries its source. A value with no source is a validator
  error.
- Every entry with a complete identity emits a runtime row. A missing
  runtime field is a labelled zero or an empty string, never a refusal of
  the record.
- `runtime_ready` reports that every runtime field resolved to a
  non-absent value. It is a report flag. It never blocks a row.
- `class_token` is an identity signal only. It never fills a value. A
  class map binds the class explicitly.

## 7. The class-to-catalogue map

Write the map at `data/vehicle/class_map.json`. It is a top-level array.
One record links one game class to one catalogue entry.

| Field | Type | Meaning |
|---|---|---|
| `game_class` | string | The exact AEE game class string. |
| `class_token` | string | The supported token from `classes.json`. |
| `catalogue_id` | string | The mapped catalogue entry. |
| `identity_source` | string | The `source_id` of the real-world mapping source. |
| `identity_evidence` | string | The words or locator that link the class to the entry. |
| `grade` | enum | `documented` or `claimed`. |
| `note` | string | An optional remark. |

Rules:

- A mapping needs a mapping source. The engine `displayName` may
  corroborate the identity. The mapping grade is `documented` when a
  tier 2 or tier 3 real-world source names the vehicle. The grade is
  `claimed` when only a tier 4 or tier 5 source does.
- An engine `class_table` or `engine_config` source can bind a class only
  at grade `claimed`, and `identity_evidence` must name the concrete token
  or kind. It is not a real-world mapping. It exists so a supported class
  that no published source names still binds, with the claim explicit.
- No category guess may create a class map. A representative category
  mapping, for example "the token is the vehicle", is not evidence. It
  stays in the gap artefact.
- A `class_token`-only mapping, with no concrete game class and no
  mapping source, is a lead. It never becomes a mapping record.
- One game class maps to at most one catalogue entry. An ambiguous
  mapping is an error.

## 8. Grades

A grade is one exact string. The grade must agree with the source tier
and the source type.

| Grade | Allowed source |
|---|---|
| `standard` | A held tier 1 standard or specification. |
| `documented` | A tier 2 or tier 3 manual or measurement. |
| `claimed` | A tier 4 manufacturer, a tier 5 compilation, or an engine class table or config. |
| `derived` | A named formula over a held value. |
| `absent` | No value is held. The runtime row states a zero or an empty string. |

A tier 5 value is `claimed` only. A `derived` runtime value must name its
formula in the state text. The validator rejects any other grade.

The runtime projection grades every field. A held value keeps its own
grade. A derived value is `derived`. A field with no value and no
derivation is `absent`. The `documented` grade for a held value still
needs a held tier 2 or tier 3 source. The `derived` grade for a held
field still needs engine geometry and a stated `formula`.

## 9. Value field groups and the unit vocabulary

The tables below name every value field. Each field carries the unit
shown.

### Mass states

Each mass value names its state in full, for example the crew and the
fuel load. A mass without a state is not usable.

| Field | Unit | Meaning |
|---|---|---|
| `operating_weight_kg` | kg | Operating weight in the stated state. |
| `curb_weight_kg` | kg | Curb weight, no crew and no payload. |
| `gross_weight_kg` | kg | Gross vehicle weight, the rated maximum. |
| `payload_kg` | kg | Payload capacity in the stated state. |

### Dimensions

| Field | Unit | Meaning |
|---|---|---|
| `length_mm` | mm | Overall length. |
| `width_mm` | mm | Overall width. |
| `height_mm` | mm | Overall height in the stated state. |
| `wheelbase_mm` | mm | Distance between the front and rear axles. |
| `track_mm` | mm | Track or wheel centre to centre distance. |
| `ground_clearance_mm` | mm | Lowest point to ground, laden state. |

### Tyres

| Field | Unit | Meaning |
|---|---|---|
| `tyre_width_mm` | mm | Tyre section width. |
| `tyre_diameter_mm` | mm | Tyre outside diameter. |
| `tyre_pressure_kpa` | kPa | Rated tyre pressure. |
| `tyre_size_text` | text | The published tyre size code. It never fills `tyre_width_mm` or `tyre_diameter_mm`. |
| `wheel_count` | count | Number of wheel stations. |
| `axle_count` | count | Number of axles. |

### Tracks

A tracked record carries these fields. It never requires a tyre field.
Section 10 gives the tracked required set.

| Field | Unit | Meaning |
|---|---|---|
| `track_shoe_width_mm` | mm | Track shoe width. |
| `track_pitch_mm` | mm | Track pitch, the pin to pin distance. |
| `track_shoe_count` | count | Number of shoes per side. Optional. It never replaces `track_pitch_mm`. |

### Power

| Field | Unit | Meaning |
|---|---|---|
| `net_power_kw` | kW | Net engine power at the rated speed. |
| `published_power_hp` | hp | The published engine rating, with its basis in the state. It never fills `net_power_kw`. |
| `engine_model` | text | Maker and model of the engine. |
| `engine_displacement_l` | L | Engine swept volume. |
| `torque_nm` | N m | Peak torque at the stated speed. |

The held manuals publish a maximum rating and no net basis. Record that
figure as `published_power_hp`, with the state `maximum rating, no net
basis`. It never fills `net_power_kw`.

### Drivetrain

| Field | Unit | Meaning |
|---|---|---|
| `drivetrain` | enum | The source phrase for the drive arrangement. |
| `transmission_type` | enum | One of `manual` or `automatic`. |
| `gears` | count | Number of forward gear ratios. |
| `final_drive` | ratio | Final drive ratio. |

### Fording

| Field | Unit | Meaning |
|---|---|---|
| `fording_depth_mm` | mm | Rated fording depth without a kit. |
| `wading_depth_mm` | mm | Rated wading depth with a kit. |

### Slope

| Field | Unit | Meaning |
|---|---|---|
| `max_gradient_deg` | deg | Maximum climb gradient. |
| `max_side_slope_deg` | deg | Maximum side slope. |
| `approach_angle_deg` | deg | Approach angle. |
| `departure_angle_deg` | deg | Departure angle. |
| `breakover_angle_deg` | deg | Breakover angle. |

### Towing

| Field | Unit | Meaning |
|---|---|---|
| `towing_capacity_kg` | kg | Rated towing capacity. |
| `trailer_braked_kg` | kg | Braked trailer limit. |
| `trailer_unbraked_kg` | kg | Unbraked trailer limit. |

### Mobility limits

| Field | Unit | Meaning |
|---|---|---|
| `max_speed_kmh` | km/h | Maximum road speed. |
| `range_km` | km | Operating range in the stated state. |
| `turning_radius_m` | m | Turning radius. |

### NRMM inputs

The NRMM model needs the inputs in section 10. A record that cannot
supply them is not runtime-ready.

| Field | Unit | Meaning |
|---|---|---|
| `grousers_state` | enum | One of `none`, `grousers` or `chains`. |

### Unit vocabulary

A unit is one exact string. The allowed strings are `kg`, `mm`, `kPa`,
`kW`, `hp`, `L`, `N m`, `deg`, `km/h`, `km`, `m`, `count`, `ratio`,
`enum` and `text`. The non-physical tokens mean this.

- `count`: a whole number of items.
- `ratio`: a dimensionless ratio.
- `enum`: one term from a stated controlled vocabulary.
- `text`: a proper name or a published code, for example an engine model
  or a tyre size code.

## 10. Runtime-required sets

The type set is the NRMM input set for the vehicle type. Every catalogue
entry with a complete identity emits one runtime row. A row resolves each
field in the order below.

1. A held value under its runtime name. The grade comes from the value
   object.
2. Else a named derivation from the table below, at grade `derived`. The
   `state` names the formula, its basis and any caveat.
3. Else a labelled zero: `0` for a numeric field, `""` for a text field,
   at grade `absent`.

A record is `runtime_ready` when every field in its type set resolves to a
non-absent value. The flag is a report. It never blocks the row.

| Runtime field | Derivation when no value is held |
|---|---|
| `operating_weight_kg` | `curb_weight_kg`, else `gross_weight_kg`. The state names the basis and any caveat. |
| `net_power_kw` | `published_power_hp * 0.745699872`. The state names the ISO 80000-4 mechanical horsepower and the brake, not net, basis. |
| `tyre_width_mm` | From `tyre_size_text`. Metric `395/85R20`: width `395`. Inch `14:00 x R20`: width `14.00 * 25.4`. |
| `tyre_diameter_mm` | From `tyre_size_text`. Metric: `rim * 25.4 + 2 * width * aspect / 100`. Inch: `(rim + 2 * width) * 25.4`, aspect 100. |
| `track_shoe_width_mm` | None. Absent is `0`. |
| `track_pitch_mm` | None. Absent is `0`. |
| `transmission_type` | None. Absent is `""`. |
| `grousers_state` | None. Absent is `""`. |

Wheeled required set:

| Required field | Unit |
|---|---|
| `operating_weight_kg` | kg |
| `tyre_width_mm` | mm |
| `tyre_diameter_mm` | mm |
| `ground_clearance_mm` | mm |
| `net_power_kw` | kW |
| `transmission_type` | enum |
| `grousers_state` | enum |

Tracked required set:

| Required field | Unit |
|---|---|
| `operating_weight_kg` | kg |
| `track_shoe_width_mm` | mm |
| `track_pitch_mm` | mm |
| `ground_clearance_mm` | mm |
| `net_power_kw` | kW |
| `transmission_type` | enum |
| `grousers_state` | enum |

A tracked record never requires `tyre_width_mm` or `tyre_diameter_mm`.
It may carry them as optional values only when a source publishes them,
and that is unusual.

A record that misses one required field is not runtime-ready. The
generator emits no row for it. The validator reports a `runtime_ready`
record that misses a required field as an error. A lead emits no row.

## 11. The matcher result

The generated file
`addons/mobility/functions/fnc_getVehicleData.sqf` carries the table, the
normaliser, the index and the ladder. The generator
`tools/validation/gen_vehicle_data.py` writes it. The runtime function
`fnc_getVehicleMatch(className)` returns the full result. The function
`fnc_getVehicleData(className [, variantId])` is a thin consumer that
returns `valueRow` or `[]`.

The matcher result is a flat array:

```
[catalogue_id, variant_id, vehicle_type, confidence, matched_by,
 source_record_id, valueRow]
```

It is `[]` when no match exists.

The ladder runs in this order. Each layer carries one confidence.

1. `exact_class`: the normalised class equals a mapped game class.
2. `alias`: a classname token or displayName token equals a catalogue
   alias.
3. `keyword`: the normalised query contains a catalogue keyword of at
   least four characters.
4. `inheritance`: the class `isKindOf` a class token, and exactly one
   catalogue entry carries that token.
5. `closest`: the candidate with the longest alias or keyword substring
   of the normalised query. The score is at least four. The runner-up
   score is strictly lower. This mirrors the longest-substring scan in
   the weapon resolver and the nearest-caliber threshold in the caliber
   parser.

Rules:

- A layer returns the first layer that yields exactly one candidate. A
  weaker layer runs only when the stronger layer yields none.
- A tie at any layer, meaning two or more candidates tie, returns `[]`.
- `matched_by` is one of `exact_class`, `alias`, `keyword`,
  `inheritance`, `closest`.
- `confidence` is an integer. It is 1 for `exact_class` and 5 for
  `closest`.
- A runtime row is emitted for every catalogue entry with a complete
  identity. A missing value does not refuse the row.
- The matcher reads no config value as a figure. It may call `isKindOf`
  and `configOf` for identity only.
- A query that matches no layer returns `[]`. A tie returns `[]`. There
  is no default and no guess.

`valueRow` is a flat array by vehicle type. A wheeled row holds
`operating_weight_kg`, `tyre_width_mm`, `tyre_diameter_mm`,
`ground_clearance_mm`, `net_power_kw`, `transmission_type` and
`grousers_state`. A tracked row holds the same columns, but
`track_shoe_width_mm` and `track_pitch_mm` replace the two tyre columns.

## 12. Generated coverage and gap artefacts

The generator `tools/validation/gen_vehicle_coverage.py` emits four
artefacts. Each artefact is deterministic. Each artefact has a `--check`
staleness mode.

| Artefact | Content |
|---|---|
| `data/vehicle/coverage.json` | One row per class token with a state. |
| `data/vehicle/COVERAGE_AUDIT.md` | Per-token runtime coverage and mapped entries. |
| `data/vehicle/SOURCE_GAPS.md` | One row per catalogue entry for each missing runtime-required field and the next source class to try. |
| `data/vehicle/CLASS_MAPPING_GAPS.md` | Each ground token and game class with no sourced mapping. |

A token state is `recorded`, `lead`, `no_source` or
`excluded_non_ground`. A `recorded` token has an emitted runtime row and a
class-map binding for the token. A `lead` token has a researched candidate
and no recorded row. A token never leaves the inventory in silence. The
audit reports the recorded count and the emitted runtime row count.

## 13. Conflicts

Two sources can disagree. Record the disagreement in `conflicts` and keep
both values. Never average two sources. Never discard one value in
silence.

One conflict record has these fields.

```json
{
  "entity": "<catalogue_id>",
  "field": "<field name>",
  "value_a": "<value>",
  "source_a": "<source_id>",
  "value_b": "<value>",
  "source_b": "<source_id>",
  "resolution": "<how the record keeps both>",
  "rule_applied": "<the rule>",
  "date": "<retrieval date>"
}
```

The record keeps both values, each keyed by its state. An averaged value
is an error and the validator rejects it. A disagreement about a unit or
a state is a conflict, not a conversion.

## 14. Fail-closed rules

A missing datum makes no result. Never invent a value. Never use a
default. Never let a zero read as a figure.

1. An unknown game class makes the matcher return `[]`.
2. An entry with a complete identity emits a runtime row. A field with no
   held value and no derivation is a labelled zero or an empty string.
3. A token with no emitted row and no class-map binding is a lead or a
   `no_source` token. It is never `recorded`.
4. A tie at any matcher layer makes the matcher return `[]`.
5. Two entries for one class with no variant selector make the matcher
   return `[]`.
6. A catalogue entry whose values miss a unit, a source, a state or a
   grade is a validator error. The validator exits 1.
7. A class map with no real-world mapping source is a validator error.
8. The matcher reads no config, reads no source registry and returns no
   default.
9. A class token with no entry appears in `data/vehicle/coverage.json`
   with a reason. It never disappears in silence.

The no-result cases are an unknown class, an incomplete entry, a lead, an
ambiguous variant, a tie and a missing required field.

## 15. Rules

1. Real published data only. An engine value is identity or geometry
   evidence and never a value source.
2. Primary sources first. Use a held primary document. Use an Internet
   Archive copy when the live site blocks, and mark the copy as such.
3. A tier 5 source is a last resort at grade `claimed` only.
4. Record a disagreement in `conflicts`. Keep both values. Never
   average.
5. One entry per real variant. A product family with published variants
   gets one entry per variant.
6. A class map needs a real-world mapping source. No category guess.
7. Write only your own output file. Never edit another file and never
   commit.
