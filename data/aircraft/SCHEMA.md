# Aircraft corpus source schema

This document defines the aircraft corpus contract. It inherits the five
layers, the source registry, the source tiers, the source types, the value
object, the catalogue entry fields, the class-map and class-binding fields,
the grades, the unit vocabulary and the runtime resolution ladder from
`data/vehicle/SCHEMA.md` by reference. It states only the aircraft deltas.
The vehicle document stays the first source for every shared rule.

This document holds no aircraft data. It ships no catalogue entry, no source
record and no class map. The registry holds the source records. The
catalogue holds the entries. The class map and the class bindings hold the
links. The layer model is in `data/aircraft/INDEX.md`.

Cite the governing rules in a change record: JSP 945 for configuration
management, Def Stan 05-138 for cyber security, and the MOD-first source
order. The source order is UK MOD first, NATO second, US DOD last, then a
manufacturer and then a compilation. A later tier never displaces an earlier
tier for the same entity and field.

## 1. The type enum

The loader key stays `vehicle_type`. The aircraft values are `fixed_wing`
and `rotary_wing`. An aircraft entry never carries `wheeled`, `tracked`,
`air` or `sea`. The type selects the runtime-required set in section 4.

## 2. The units added

The aircraft unit vocabulary adds `kN`, `m/s` and `m^2` to the shared
vocabulary. The vocabulary in `data/vehicle/SCHEMA.md` section 9 stays in
force. `kN` is a kilonewton. `m/s` is a metre per second. `m^2` is a
square metre.

## 3. The field list and the model mapping

An aircraft value field is one object from the inherited value object. The
table below gives each field, its unit, its consuming model and its
derivation. The four calculation inputs are `operating_weight_kg`,
`rated_power_w`, `drag_area_m2` and `rotor_disc_area_m2`. Every other field
is reference-only. A reference-only field documents the airframe. It never
fills a calculation input.

| Field | Unit | Consuming model | Derivation when not held |
|---|---|---|---|
| `operating_weight_kg` | kg | kernel `_massKg`; turbulence `getMass` basis | from `empty_weight_kg`, else `max_takeoff_weight_kg`. The state names the basis. |
| `rated_power_w` | W | kernel `_ratedPowerW` | See section 5. |
| `drag_area_m2` | m^2 | kernel `_dragAreaM2`, fixed-wing only, optional | `drag_coefficient * wing_area_m2` when both are held. Else it is absent. |
| `rotor_disc_area_m2` | m^2 | kernel `_rotorDiscAreaM2`, rotary only | `pi * (rotor_diameter_m / 2)^2`. The state names the formula. |

The derivation inputs are held and not directly consumed:
`empty_weight_kg`, `max_takeoff_weight_kg`, `net_power_kw`,
`published_power_hp`, `thrust_kn`, `reference_speed_ms`,
`rotor_diameter_m`, `drag_coefficient` and `wing_area_m2`.

Use one name for one quantity. Use `reference_speed_ms` only. A source that
publishes km/h is converted to m/s at capture time. The locator records the
conversion.

The reference-only fields are `length_m`, `height_m`, `wing_span_m`,
`rotor_diameter_m`, `max_speed_kmh`, `cruise_speed_kmh`, `range_km`,
`service_ceiling_m`, `rate_of_climb_ms`, `payload_kg`, `crew`, `capacity`,
`engine_model`, `engine_count`, `first_flight`, `country`, `role` and
`propulsion`.

`propulsion` is one of `turbofan`, `turbojet`, `turboprop`, `piston_prop`,
`turboshaft`, `piston_rotor`. `role` is one of `multirole`, `interceptor`,
`attack`, `bomber`, `transport`, `trainer`, `recon`, `utility`, `gunship`,
`liaison`.

## 4. Runtime-required sets

The type set is the flight-model input set for the aircraft type.

| Type | Runtime-required fields |
|---|---|
| `fixed_wing` | `operating_weight_kg`, `rated_power_w` |
| `rotary_wing` | `operating_weight_kg`, `rated_power_w`, `rotor_disc_area_m2` |

`drag_area_m2` is a fixed-wing value field. It is optional. The runtime uses
it when it is held. The kernel default `0.7` stands when it is absent.

A record is `runtime_ready` when every field in its type set resolves to a
non-absent value. The flag is a report. It never blocks the row.

## 5. The named derivations

Four named derivations apply. Each sets the grade to `derived`. Each names
its formula in the `state` text. The generator writes the marker and the
validator checks it. The inherited rules for a derived value stay in force.

| Runtime field | Formula | Basis |
|---|---|---|
| `operating_weight_kg` | value of the basis | `empty_weight_kg`, else `max_takeoff_weight_kg` |
| `rated_power_w`, jet | `thrust_kn * 1000 * reference_speed_ms` | when `thrust_kn` is held |
| `rated_power_w`, prop or rotor | `net_power_kw * 1000` | when `thrust_kn` is not held |
| `rated_power_w`, fallback | `published_power_hp * 745.699872` | when only the horsepower is held |
| `rotor_disc_area_m2` | `pi * (rotor_diameter_m / 2)^2` | when `rotor_diameter_m` is held |
| `drag_area_m2` | `drag_coefficient * wing_area_m2` | when both are held |

The `rated_power_w` derivation selects the jet formula when `thrust_kn` is
held. It selects the prop or rotor formula from `net_power_kw` otherwise. It
selects `published_power_hp` last. `propulsion` is a descriptive field. It is
not a resolver argument.

## 6. The UNSOURCED marker rule

A value whose only source is unheld or proprietary takes the grade
`claimed`. Its source record carries `primary_held: false`. The `state` text
must start with the marker `UNSOURCED`. Such a value is a lead. It never
fills a runtime-required field. The generator emits no runtime value from
it. The validator rejects an UNSOURCED value in a runtime-required field.
The coverage artefact records the entry as a gap.

## 7. The four air tokens

The aircraft class inventory reads the four existing air tokens from
`data/vehicle/classes.json`: `Air`, `Helicopter`, `Plane` and `UAV`. The
corpus adds no `data/aircraft/classes.json`. The concrete class bindings
live in `data/aircraft/class_bindings.json`. `UAV` is in scope. It lands a
`no_source` state until a real-world mapping exists.

## 8. Aircraft fail-closed additions

The inherited fail-closed rules apply in full. The aircraft additions are
these.

1. A `fixed_wing` or `rotary_wing` entry with no held or derived
   `operating_weight_kg` is a lead. It emits no runtime row value.
2. An UNSOURCED value never fills a runtime-required field.
3. The matcher reads no config value as a figure. A class token and a
   config name are identity signals only.
4. A class binding with no real-world mapping source stays a lead. It never
   becomes a binding record.

## 9. Rules

1. Real published data only. An engine value is identity or geometry
   evidence and never an aircraft value source.
2. Primary sources first. Use a held primary document.
3. A tier 5 source is a last resort at grade `claimed` only.
4. Record a disagreement in `conflicts`. Keep both values. Never average.
5. One entry per real variant.
6. A class binding needs a real-world mapping source. No category guess.
7. Write only your own output file. Never edit another file and never
   commit.

## 10. The aircraft systems deltas

This section inherits the shared systems field contract from
`data/vehicle/SCHEMA.md` section 16 by reference. It states only the
aircraft additions. The shared fuel, engine, mass, damage and status
tables stay in force. They are not restated here.

A row below carries the same shape as a shared row: a unit, a source
class, a published flag and an engine hook or marker.

### The aircraft engine ceiling

The engine ceiling in `data/vehicle/SCHEMA.md` section 16 applies. The
aircraft addition is the turbine delta. The RotorLib real-time data
interface exists only when `difficultyEnabledRTD` is true. The commands
are `setWantedRPMRTD` and the real-time getters. The interface is a no-op
in the simple model. The engine exposes no turbine temperature, no oil, no
start and no wear. The script supplies the turbine-temperature and oil
readout. The flight dynamics model is fixed at config load.

### The status-systems ceiling

The status-systems ceiling is stated once in `data/vehicle/SCHEMA.md`
section 16. It applies here in full. Hydraulics, electrical and
pressurisation are absent and status only. No second statement is needed.

### Engine turbine terms

| Field | Unit | Source class | Published | Engine hook or marker |
|---|---|---|---|---|
| `engine_design_rpm` | rpm | manual | yes | systems row, the RTD RPM base |
| `engine_idle_ng` | ratio | manual | yes | `setWantedRPMRTD` target, RTD only |
| `engine_max_ng` | ratio | manual | yes | `setWantedRPMRTD` limit, RTD only |
| `engine_max_np` | ratio | manual | yes | scripted status |
| `engine_max_tgt_c` | deg C | manual | yes | scripted status, not engine-exposed |
| `engine_max_itt_c` | deg C | manual | yes | scripted status |
| `transmission_gear_ratio_tail` | ratio | manual | yes | reference only |

### Rotor geometry

| Field | Unit | Source class | Published | Engine hook or marker |
|---|---|---|---|---|
| `rotor_radius_m` | m | manual | yes | reference only, disc area derivation |
| `rotor_diameter_m` | m | manual | yes | exists |
| `rotor_blade_count` | count | manual | yes | reference only |
| `rotor_chord_m` | m | manual | yes | reference only |
| `rotor_twist_deg` | deg | manual | yes | reference only |
| `rotor_hinge_offset_m` | m | manual | yes | reference only |
| `rotor_design_rpm` | rpm | manual | yes | reference only |
| `rotor_tip_speed_ms` | m/s | derived | no | reference only |
| `tail_rotor_radius_m` | m | manual | yes | reference only |
| `tail_rotor_blade_count` | count | manual | yes | reference only |

### V-speeds

| Field | Unit | Source class | Published | Engine hook or marker |
|---|---|---|---|---|
| `vne_kmh` | km/h | manual / poh | yes | reference only |
| `vmo_kmh` | km/h | manual | yes | reference only |
| `vref_kmh` | km/h | manual | yes | reference only |
| `vstall_kmh` | km/h | manual | yes | reference only |
| `vy_kmh` | km/h | manual | yes | reference only |
| `autorotation_speed_kmh` | km/h | manual | yes | reference only |
| `service_ceiling_m` | m | manual | yes | exists |

### Pressurisation

| Field | Unit | Source class | Published | Engine hook or marker |
|---|---|---|---|---|
| `cabin_pressure_max_kpa` | kPa | manual | yes | status only |
| `pressurisation_ceiling_m` | m | manual | yes | status only |
| `oxygen_system` | enum | manual | yes | status only |

## 11. The fictional-class analogue rule

A fictional Arma class binds to a real analogue. The binding is a claim. This
section states the rule and the licence boundary.

### The rule

1. A fictional Arma class never reaches grade `documented` for its identity. No
   published source names a fictional class, so the class-to-analogue link is
   always grade `claimed`. A held source that states the analogue's figures does
   not raise the identity grade.
2. The binding `identity_source` is a registered source. Use
   `src_armedassault_wiki` (tier 5 compilation) when the community wiki names the
   analogue. Use `aee_air_class_table` (tier 5 class table) otherwise. A
   class-table binding names the concrete class token in its `identity_evidence`.
3. The catalogue entry the binding points to carries values only from held
   sources. A tier 2 or tier 3 held source gives grade `documented`. A tier 4
   maker datasheet gives grade `claimed`. A tier 5 compilation is never a value
   source.
4. The `identity_evidence` names the concrete game class, the real analogue, the
   judgement, and the held source that documents the analogue's figures.
5. A held source that states no runtime-required figure gives an absent value,
   never an invented one. A family with no held analogue keeps its `no_source`
   state. Its reason names the exact next source and the licence of that source.
6. The claimed-lead mechanism. A registered source may name a single analogue
   while no held source states its figures. A `claimed` binding may then point
   to a lead entry. The lead entry holds no value and names its next source.
   This document records the mechanism. It does not apply the mechanism.

### The licence boundary

The allowed value sources are these:

- US Government public-domain works: TMs, FMs, TOs, the OPFOR and ODIN
  Worldwide Equipment Guides, and DTIC and NASA reports.
- FAA and EASA type certificate data sheets.
- Maker datasheets, with the facts cited.
- CC-BY-SA compilations for identity only.

The forbidden sources are these:

- RHS (CC BY-NC-ND).
- CUP (APL-SA).
- Project Hatchet H-60 and BradMick HeliSim (APL-ND).
- DCS. It is structure only and never a figure.
