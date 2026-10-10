# Aircraft corpus index

The aircraft corpus gives every supported AEE air class a source-backed
real-world counterpart. The corpus holds the only real aircraft values. The
game config is identity evidence. The generated runtime lookup returns no
result when the class or a field is unknown.

Read `data/vehicle/INDEX.md` for the shared layer model. Read
`data/vehicle/SCHEMA.md` for the catalogue contract, the class map, the value
object, the source tiers, the grades and the fail-closed rules. Read
`data/aircraft/SCHEMA.md` for the aircraft deltas: the type enum, the units
added, the field list, the runtime-required sets, the named derivations, the
UNSOURCED marker rule and the optional fixed-wing drag area.

## 1. Layers

The corpus keeps the five vehicle layers apart. Each layer has one owner and
one output. The vehicle layer model in `data/vehicle/INDEX.md` section 1
stays in force. The aircraft deltas are these.

### 1.1 Class identity

Class identity is the AEE game class and its supported class token. The
inventory reads the four existing air tokens from `data/vehicle/classes.json`:
`Air`, `Helicopter`, `Plane` and `UAV`. The corpus adds no
`data/aircraft/classes.json`. A class token is an identity signal only. It
never fills a value.

### 1.2 Real-world catalogue entry

A real-world catalogue entry is one real maker, model and variant. One entry
holds one variant. The entry carries the fields in `data/vehicle/SCHEMA.md`
section 6. The aircraft delta is the type enum: `fixed_wing` or
`rotary_wing`, under the loader key `vehicle_type`. Write one capture file
for each held source at `data/aircraft/catalogue/<source_id>.json`.

### 1.3 Class-to-catalogue map

The class-to-catalogue map is the recorded link from one game class to one
catalogue entry. The aircraft copies are `data/aircraft/class_map.json` and
`data/aircraft/class_bindings.json`. The fields and the rules are in
`data/vehicle/SCHEMA.md` section 7. A real-world source that names the
aircraft grades the link `documented`. A category guess is not a mapping.

### 1.4 Source record

A source record is one held document. The registry is
`data/aircraft/sources.json`. The held documents live under
`data/aircraft/sources/`. The held bytes stay out of git. The register and
the digest stay in git. The fields are in `data/vehicle/SCHEMA.md` section 2.

### 1.5 Generated runtime projection

The generated runtime projection is an SQF matcher. The generator
`tools/validation/gen_aircraft_data.py` writes
`addons/flight/functions/fnc_getAircraftData.sqf`. The file is never
edited by hand. The matcher uses the inherited five-layer ladder. The
runtime fields are `operating_weight_kg`, `rated_power_w`, `drag_area_m2`
and `rotor_disc_area_m2`. The projection reads no config and no registry at
runtime. It returns `[]` when the class is unknown or the match is
ambiguous.

## 2. Pipeline

The stages run in this order. Each stage writes one output.

1. Derive the air class inventory from the four air tokens in
   `data/vehicle/classes.json`.
2. Write the sources into `data/aircraft/sources.json`.
3. Write the catalogue entries into `data/aircraft/catalogue/`.
4. Write the class-to-catalogue map into `data/aircraft/class_map.json`.
5. Write the concrete bindings into `data/aircraft/class_bindings.json`.
6. Validate the corpus with `tools/validation/validate_aircraft_data.py`.
7. Generate the coverage and gap artefacts with
   `tools/validation/gen_aircraft_coverage.py`.
8. Generate the projection with `tools/validation/gen_aircraft_data.py`.
9. Generate the systems lookup with
   `tools/validation/gen_aircraft_systems.py`.
10. Project the load-time config with
    `tools/validation/gen_physics_config.py`.
11. Run the freshness gates. Each generated file has a `--check` mode and
    exits 1 on a stale file.

The validator is the gate. It rejects an unsourced value, a config-derived
value, a missing unit, a missing state and a bad grade coupling. It rejects
an UNSOURCED value in a runtime-required field. It requires a derived value
to name its formula. It exits 1 on an error.

## 3. Files

| Path | Layer | Role |
|---|---|---|
| `data/aircraft/SCHEMA.md` | contract | The aircraft deltas to the vehicle contract. |
| `data/aircraft/INDEX.md` | contract | This layer model. |
| `data/aircraft/sources.json` | source | The held document registry. |
| `data/aircraft/sources/` | source | The held bytes. |
| `data/aircraft/catalogue/` | entry | One capture file per held source. |
| `data/aircraft/class_map.json` | map | The class-to-catalogue links. |
| `data/aircraft/class_bindings.json` | map | The concrete game-class bindings. |
| `data/aircraft/fixtures/` | entry | Deliberate invalid test fixtures. Never production entries. |
| `data/aircraft/coverage.json` | coverage | A state for every air token and every roster class. |
| `data/aircraft/COVERAGE_AUDIT.md` | coverage | Generated per-token and per-class coverage. |
| `data/aircraft/SOURCE_GAPS.md` | coverage | Generated per-entry missing fields. |
| `data/aircraft/CLASS_MAPPING_GAPS.md` | coverage | Generated unmapped classes and tokens. |
| `data/aircraft/RESEARCH_GAPS.md` | entry | The hand-written lead and data-gap register. |
| `tools/validation/gen_aircraft_systems.py` | generator | Writes the systems lookup from the corpus. |
| `addons/flight/functions/fnc_getAircraftSystems.sqf` | generated | The fixed-order systems row. It returns `[]` for an unknown class. |
| `addons/vehicles/generated/CfgVehicles.hpp` | generated | The load-time config, the aircraft `fuelCapacity` and the land physics keys. |

The `data/aircraft/fixtures/` layer holds a deliberate invalid pilot
fixture. It is a negative-test and audit artefact. The validator must reject
it. It is outside the catalogue path, so the production corpus holds no
invalid entry.

The layer also holds `fixtures/sources.json`. That file keeps the fixture
source entries out of the production registry. The production registry holds
real held documents only.

## 4. Coverage table

The coverage guard gives every air token in the inventory one state and every
roster class one state. The token states are `recorded`, `lead`, `no_source`
and `excluded_non_ground`. A token never leaves the inventory in silence. A
`recorded` token has an emitted runtime row and a class binding. The audit
reports both the recorded count and the emitted runtime row count.

The coverage payload holds two keyed tables. The `tokens` table is keyed by
the engine class token. The `classes` table is keyed by the concrete game
class in `data/aircraft/roster.json`. A class is `recorded` only when an
emitted runtime row AND a class binding both hold. A class with a roster
`no_source_reason` is `no_source`. Any other class is `lead`. Every roster
class appears once, so no class leaves the report in silence.

The table below is a stub. The coverage guard fills the rows. The stub names
no class.

| Token | Kind | Air | State | Entry | Reason |
|---|---|---|---|---|---|
| | | | | | |

The expansion coverage target is every air class in the deployed
inventory, matched to a real type with a sourced spec or recorded as
`no_source` with a reason. A class with no real counterpart is recorded
as `no_source`. No analogue is invented. The coverage artefact reports
the target. The count of `recorded` classes plus `no_source` classes
equals the roster size.

## 5. Fail-closed summary

The matcher returns no result in these cases. They are an unknown class, an
identity-incomplete entry, an ambiguous variant and a tie at one match
layer. The runtime projection returns `[]` in every case. It never returns a
default.

A missing field is not a no-result case. A labelled weak value beats a
silent zero: the row states a graded value for every runtime field. A field
with no held value and no derivation is a zero for a number, graded
`absent`. The grade and the derivation basis are reported in the coverage
and source-gap artefacts.

The aircraft additions to the fail-closed rules are in
`data/aircraft/SCHEMA.md` section 8. The runtime-required fields are the per
type sets in `data/aircraft/SCHEMA.md` section 4.

## 6. Status

This document and the schema define the contract. The contract is complete.
The corpus holds 226 catalogue entries across 13 capture files. Thirteen
entries are runtime-ready and the rest are leads. The registry holds 35
sources, 18 of them held. The class map holds two token bindings and the
class bindings hold 99 concrete vanilla and DLC classes.

The coverage guard gives the four air tokens one state each and the 139
roster classes one state each. The tokens `Plane` and `Helicopter` are
`recorded`. The tokens `Air` and `UAV` are `no_source`. The roster classes
are 99 `recorded` and 40 `no_source`. The count of recorded classes plus
`no_source` classes equals the roster size. The generated projection is
current.

The first slice names the four air tokens and the vanilla air classes. Each
one maps to a real analogue and a sourced catalogue entry. A class name that
fails config verification drops to `CLASS_MAPPING_GAPS.md`. It does not
block the slice.

The governing rules are JSP 945 for configuration management and
Def Stan 05-138 for cyber security. The source order is UK MOD first, NATO
second, US DOD last, then a manufacturer and then a compilation.

## 7. The systems layers

The systems fields extend the corpus. They do not change the layer model
or the four-value runtime projection. The systems pieces are these.

- The shared contract. `data/vehicle/SCHEMA.md` section 16 defines the
  family-agnostic systems fields. Section 17 defines the land-vehicle
  physics surface. `data/aircraft/SCHEMA.md` section 10 states only the
  aircraft deltas.
- The systems lookup. `tools/validation/gen_aircraft_systems.py` writes
  `addons/flight/functions/fnc_getAircraftSystems.sqf`. It returns a
  fixed-order systems row for a known class and `[]` for an unknown class.
  It reads no config value and no source registry at runtime.
- The runtime kernels and driver. The kernel set holds the fuel burn and
  the centre-of-gravity shift, the engine limits and the scripted turbine
  temperature and oil readout, the damage on the engine hit points, and
  the status-only readout. One per-frame driver schedules the four
  kernels.
- The status-only ceiling. Hydraulics, electrical and pressurisation are
  absent from the engine. They are status only. A status-only value never
  feeds the flight dynamics model. The aircraft engine ceiling is in
  `data/aircraft/SCHEMA.md` section 10.
