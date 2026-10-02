# Device corpus source schema

The device corpus is the only home for a real night vision, thermal or
optic device value. Every value carries a unit, a source, a locator, a
state and a grade. A loader rejects any value without them. The generated
runtime projection reads the corpus, not a game config.

This document defines the contract. It holds no device data. It ships no
catalogue entry and no class list. The source registry holds the documents.
The catalogue holds the entries.

Cite the governing rules in a change record: JSP 945 for configuration
management, Def Stan 05-138 for cyber security, and the MOD-first source
order in `data/vehicle/SCHEMA.md`.

## 1. The layers

The corpus has four layers. Keep them apart.

1. Device identity. The device id, the family and the real class names.
2. Device entry. The real maker, model and variant, with aliases,
   keywords and per-field sources.
3. Source record. The held document with its tier, type and locator.
4. Generated runtime projection. The SQF matcher and the lookup built
   from layers 1 to 3. It does no runtime source lookup.

A layer never borrows a value from another layer. A class name and the
engine `displayName` are identity signals only. They are never a value.

## 2. The source registry

Write the registry at `data/device/sources.json`. It is a top-level array.
One entry is one held document.

Required fields are `source_id`, `tier`, `type` and `title`. Expected
fields are `edition`, `identifier`, `locator`, `published`, `retrieved`,
`url`, `primary_held` and `note`.

- `source_id`: stable snake_case key. One id per document.
- `tier`: the source tier. Section 3 gives the order.
- `type`: `standard`, `manual`, `measurement`, `manufacturer` or
  `compilation`.
- `primary_held`: true only when the primary document is held.

## 3. Source tiers and order

The order is UK MOD first, NATO second, US DOD last.

1. Tier 1: an issued standard or specification.
2. Tier 2: a military manual or a technical manual.
3. Tier 3: a reference work or a peer-reviewed measurement.
4. Tier 4: a manufacturer datasheet or product page.
5. Tier 5: a compilation.

A tier 5 entry is allowed at grade `claimed` only. It never displaces a
tier 1 to tier 4 value. Reach for a compilation only when nothing stronger
exists.

## 4. The value object

Every value field is an object with these six keys.

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
  published precision.
- `unit`: an exact string from the unit vocabulary in section 6. It must
  agree with the field unit. A missing unit is an error.
- `source`: the `source_id` of the held document. The id must exist in
  `data/device/sources.json`.
- `locator`: the page, table or row that carries the value.
- `state`: the configuration the value belongs to.
- `grade`: one of the grades in section 5. A tier 5 source is `claimed`
  only.

A placeholder in angle brackets is not data. Replace every placeholder
with a sourced value.

## 5. Grades

| Grade | Allowed source |
|---|---|
| `standard` | A held tier 1 standard or specification. |
| `documented` | A tier 2 or tier 3 manual or measurement. |
| `claimed` | A tier 4 manufacturer or a tier 5 compilation. |
| `derived` | A named formula over a held value. |
| `absent` | No value is held. The runtime row states a zero or an empty string. |

The runtime projection grades every field. A held value keeps its own
grade. A field with no value is `absent`.

## 6. Value fields and the unit vocabulary

The unit vocabulary is `enum`, `lp/mm`, `ratio`, `mm`, `C`, `count`,
`Hz`, `kg`, `deg` and `text`. The non-physical tokens mean this.

- `enum`: one term from a stated controlled vocabulary.
- `count`: a whole number of items.
- `ratio`: a dimensionless ratio.

### Image intensifier fields

| Field | Unit | Meaning |
|---|---|---|
| `output_colour` | enum | `green` (P43) or `white` (P45). |
| `resolution_lpmm` | lp/mm | Limiting resolution. |
| `snr` | ratio | Signal-to-noise ratio. |
| `halo_mm` | mm | Halo diameter at the tube face. |
| `gain` | cd/m2/lx | Luminous gain, where published. |
| `photocathode_sensitivity` | uA/lm | Where published. |

### Thermal sensor fields

| Field | Unit | Meaning |
|---|---|---|
| `netd_c` | C | Noise-equivalent temperature difference. |
| `resolution_x` | count | Detector width in pixels. |
| `resolution_y` | count | Detector height in pixels. |
| `refresh_hz` | Hz | Frame rate. |
| `cooled` | enum | `cooled` or `uncooled`. |
| `weight_kg` | kg | Device weight. |

### Optic fields

| Field | Unit | Meaning |
|---|---|---|
| `magnification` | ratio | Magnification. |
| `objective_mm` | mm | Objective diameter. |
| `fov_deg` | deg | Field of view. |
| `weight_kg` | kg | Device weight. |
| `exit_pupil_mm` | mm | Exit pupil diameter. |
| `active` | enum | `active` or `passive`. |

## 7. The catalogue entry

Write one capture file for each device family at
`data/device/catalogue/<family>_devices.json`. A capture holds `retrieved`,
`note`, `sources` and `entries`.

`sources` is a retired compatibility field. It must stay an empty array.
Register every source in `data/device/sources.json`.

| Field | Type | Meaning |
|---|---|---|
| `device_id` | string | Stable snake_case canonical id. The primary key. |
| `canonical_name` | string | The one canonical name of the device. |
| `family` | enum | `nvg`, `thermal` or `optic`. |
| `maker` | string | The real maker, or empty. |
| `country` | string | The country of origin or service. |
| `class_names` | array | Exact game class names, or close aliases. |
| `aliases` | array | Lowercase token match strings. |
| `keywords` | array | Lowercase substring match words. |
| `values` | object | The value objects, keyed by field name. |

Rules:

- `device_id` is unique in the corpus.
- `aliases` and `keywords` are lowercase. The runtime normaliser keeps
  `[a-z0-9]` only.
- A class name or alias shared by two entries of one family is an
  ambiguity. A device family with two matches is an error.
- Every value carries its source. A value with no source is a loader
  error.
- Every entry with a complete identity emits a runtime row. A missing
  field is a labelled zero or an empty string, never a refusal of the
  record.

## 8. Runtime-required sets

Every entry emits one runtime row. The row resolves each field in the
order below.

1. A held value under its runtime name. The grade comes from the value
   object.
2. Else a labelled zero: `0` for a number, `""` for a word, at grade
   `absent`.

| Family | Runtime fields, in projection order |
|---|---|
| `nvg` | `output_colour`, `resolution_lpmm`, `snr`, `halo_mm` |
| `thermal` | `netd_c`, `resolution_x`, `resolution_y`, `refresh_hz`, `cooled`, `weight_kg` |
| `optic` | `magnification`, `objective_mm`, `fov_deg`, `weight_kg`, `exit_pupil_mm`, `active` |

## 9. The generated runtime projection

The generator `tools/validation/gen_device_data.py` writes two SQF files:

- `addons/nightvision/functions/fnc_getDeviceMatch.sqf`: the identity
  ladder. It filters the table by family, then runs the layers exact
  class, alias, keyword and closest. A tie returns an empty array.
- `addons/nightvision/functions/fnc_getDeviceData.sqf`: the thin lookup
  that returns the value row.

The matcher reads the class name and the class `displayName`. It reads no
config value as a figure and no source registry. The `--check` mode writes
nothing and returns 1 when a generated file is stale.

`fnc_getNvgTubeModel` reads the generated table for the night vision
family and keeps the generation fallback from `fnc_getNvgDeviceProperties`
for an unmatched device.

The governing rules are JSP 945 for configuration management and Def Stan
05-138 for cyber security.
