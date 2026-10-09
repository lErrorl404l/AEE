# Physics config-binding schema

The config-binding corpus is the only home for an engine config value. The
corpus binds one engine config key on one concrete game class to one held
catalogue value. A generated engine config override reads the corpus. It
never copies an engine value.

This document defines the contract. It holds no binding. The held values live
in `data/vehicle/`. The concrete class layer lives in
`data/vehicle/class_bindings.json`. The corpus lives in
`data/physics/config_bindings.json`. The validator
`tools/validation/validate_physics_config.py` gates the corpus.

Cite the governing rules in a change record. Configuration management is JSP
945. The source order is the MOD-first order in `data/vehicle/SCHEMA.md`.

## 1. The rule that governs everything

An engine config value is never its own source. A config `maxSpeed`, a config
`mass` and a config `enginePower` are engine values. They name engine
behaviour. They do not measure the real vehicle.

The corpus value comes from a held real-world catalogue field. A named
conversion projects that held field onto the engine config key. The engine
config value is a projection of a held value. It is not a copy of an engine
value.

Three consequences follow.

1. Every binding names a held catalogue field and its source.
2. Every binding names a conversion from the documented allowlist.
3. The validator reproduces the value from the held field and the conversion.
   A value that does not reproduce is an error.

A value with no held source is not a binding. Omit it. Do not invent it, do
not estimate it and do not copy an engine value.

## 2. The layer model

The corpus has four layers. Keep them apart.

1. Held catalogue value. A real-world value with a unit, a source, a locator,
   a state and a grade. It lives in `data/vehicle/catalogue/`.
2. Concrete class binding. One game class linked to one catalogue entry. It
   lives in `data/vehicle/class_bindings.json`.
3. Config binding. One engine config key on one game class, with a value
   produced from layer 1 by a named conversion.
4. Generated override. The engine config projection. It is generated output.

A layer never borrows a value from another layer.

## 3. The binding record

Write the corpus at `data/physics/config_bindings.json`. It is a top-level
array. One record binds one key on one class.

| Field | Type | Meaning |
|---|---|---|
| `game_class` | string | The exact concrete AEE game class. It must resolve in `data/vehicle/class_bindings.json`. |
| `config_class` | string | The engine config class that owns the key. This version admits `CfgVehicles` only. |
| `key` | string | The engine config key. This version admits `maxSpeed`, `fuelCapacity` and `fuelConsumptionRate`. |
| `value` | number | The projected config value. It must reproduce from the held field and the conversion. |
| `unit` | string | The config unit. `maxSpeed` is `km/h`, `fuelCapacity` is `L`, `fuelConsumptionRate` is `unitless`. |
| `value_source` | object | The held field the value traces to. Section 4 defines it. |
| `conversion` | string | One conversion name from the allowlist in section 5. |
| `grade` | enum | The provenance grade. Section 6 defines it. |

Rules:

- `game_class` is unique in the corpus. One class carries one value for one
  key. A key may not repeat on one class.
- `config_class` names identity only. It is never a value source.
- `key` names identity only. It is never a value source.
- A class with no held field for the key carries no binding. Omit the class.
- Every required field is non-empty. The validator rejects an empty field.

## 4. The value source object

Each binding carries one `value_source` object. It names the held field.

| Field | Type | Meaning |
|---|---|---|
| `source_id` | string | The `source_id` of the held value. It must exist in `data/vehicle/sources.json` and own the named field. |
| `locator` | string | The page, table or row that carries the held value. |
| `field` | string | The held catalogue field name, for example `max_speed_kmh`. |

Rules:

- `field` names a field in the bound catalogue entry. A field the entry does
  not hold is an error.
- `source_id` is the source the held value records. A different source is an
  error.
- The engine config key and the held field are two names. The conversion
  links them.

## 5. The conversion allowlist

A conversion is one exact string. It is a named formula over the held value.
The validator admits no other name.

| Conversion | Source unit | Target unit | Formula |
|---|---|---|---|
| `identity` | same as target | same as source | The value passes unchanged. This is the direct unit identity. |
| `mph_to_kmh` | `mph` | `km/h` | `value * 1.609344`. |
| `mps_to_kmh` | `m/s` | `km/h` | `value * 3.6`. |
| `structural_zero` | none | none | The value is fixed at zero. `fuelConsumptionRate` is a structural zero: it disables the engine's own burn so the scripted burn from the sourced systems row is authoritative and the two never double-count. |

Rules:

- `identity` is the direct unit identity. The source unit equals the target
  unit. The value is the held value.
- A named conversion rounds to six decimal places.
- The held unit must agree with the conversion source unit. The binding unit
  must agree with the conversion target unit.
- The `maxSpeed` key is documented in `km/h`. The binding unit must be
  `km/h`.

## 6. Grades

A grade is one exact string from the vehicle grade vocabulary, without
`absent`. A binding with no held value is omitted, so it is never `absent`.

| Grade | Meaning |
|---|---|
| `standard` | A held tier 1 standard or specification. |
| `documented` | A tier 2 or tier 3 manual or measurement. |
| `claimed` | A tier 4 manufacturer, a tier 5 compilation, or an engine source. |
| `derived` | A named formula over a held value. |

Rules:

- An `identity` binding keeps the grade of the held field. The value is the
  published value in the same unit.
- A named conversion is `derived`. The conversion changes the number.
- The grade must agree with the source tier. The vehicle schema holds the
  full grade rule.

## 7. Fail-closed rules

A missing datum makes no binding. Never invent a value. Never use a default.

1. An unknown `conversion` is an error.
2. An unknown `game_class` with no concrete class binding is an error.
3. An unknown `source_id` is an error.
4. A `source_id` that does not own the named held field is an error.
5. A value that does not reproduce from the held field and the conversion is
   an error.
6. A class whose bound catalogue entry holds no value for the key is omitted.
   A recorded binding for that class is an error.
7. An empty required field is an error.

## 8. Worked example

The M923A2 cargo truck holds a maximum road speed of 88 km/h. The source is
`tm_9_2320_272_10`. The config `maxSpeed` is in km/h. The conversion is the
direct unit identity, so the config value is 88. The grade is `documented`,
because the held value is `documented`.

```json
{
  "game_class": "B_Truck_01_transport_F",
  "config_class": "CfgVehicles",
  "key": "maxSpeed",
  "value": 88,
  "unit": "km/h",
  "value_source": {
    "source_id": "tm_9_2320_272_10",
    "locator": "Table 1-9A, Maximum Safe Operating Speeds, page 1-23, Highway/secondary roads, column W/ABS",
    "field": "max_speed_kmh"
  },
  "conversion": "identity",
  "grade": "documented"
}
```
