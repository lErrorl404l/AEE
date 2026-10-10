# ADR-032: Aircraft Systems, the Shared Contract and the Land Branch

Status: Accepted
Date: 2026-10-10
Decision: AEE adds a shared vehicle systems contract and a scripted systems layer. The aircraft family is the first consumer. The land family is a branch, not a rewrite. The engine accepts some values at config load and no command reaches the rest, so every system states its ceiling.

## Context

The aircraft corpus projected four scalars to the flight model. The operator wants fuel, engine, damage and status systems. Those systems need more fields than the four-value row carries.

The engine fixes the flight dynamics model at config load (ADR-017). The engine exposes fuel capacity and a burn rate, and it exposes the RotorLib real-time data interface only when `difficultyEnabledRTD` is true. It exposes no turbine temperature, no oil, no start and no wear.

A land vehicle uses no engine XML. The engine reads no XML for a carx, tankx or shipx vehicle. The land physics lives in the load-time `CfgVehicles` block.

The reference mods (Project Hatchet H-60 and BradMick's HeliSim) and RHS, CUP and DCS are No-Derivatives or structure-only. Only their structure is learnable. Every number comes from a primary published source.

## Decision

1. The shared contract and the aircraft delta. `data/vehicle/SCHEMA.md` section 16 holds the family-agnostic systems fields: fuel, engine, mass and centre of gravity, damage and the status systems. `data/aircraft/SCHEMA.md` section 10 holds only the aircraft delta: the turbine terms, the rotor geometry, the V-speeds and pressurisation. `data/vehicle/SCHEMA.md` section 17 holds the land-vehicle physics surface. One schema shape serves both families.

2. The load-time config projection and the one-block rule. `gen_physics_config.py` is the sole owner of one `CfgVehicles` block. One build-time predicate emits a key only when the class identity grade and the value grade are both `documented`. A `claimed` identity emits no key. Config is load-time and global, so a runtime setting cannot gate it. The PBO is the only off switch.

3. The systems lookup is separate from the flight-model row. The four-value `fnc_getAircraftData` row is untouched. A second generated lookup, `fnc_getAircraftSystems`, returns the fixed-order systems row. The pinned four-value contract and its test stay green.

4. The engine ceiling per system. Fuel is built-in partial: `fuelCapacity`, `fuelConsumptionRate` and `setFuel` exist, and the transfer, the jettison and the centre-of-gravity shift are scripted. The engine burn is set to zero, so the sourced rate drives a scripted burn and the two never double-count. The engine exposes `setWantedRPMRTD` and the RTD getters, but only under `difficultyEnabledRTD`. Turbine temperature, oil, start and wear are not exposed and are scripted. Damage is built-in: `HitPoints`, `get` and `setHitPointDamage`, `setDamage` and `allowDamage` exist, and the per-system progressive damage is scripted. Hydraulics, electrical and pressurisation are absent, so they are status only and never feed the flight dynamics model. The flight dynamics model is engine-fixed at config load.

5. The land no-XML decision and the ADR-017 extension. The engine reads no XML for a land vehicle, so the land branch consumes the shared spec through the load-time `CfgVehicles` physics block and the mobility physics. The tyre and contact solver, the gearbox shift logic, the suspension and the engine-power curve are engine-owned. AEE owns only bounded force deltas on the owner machine and never calls `setVelocity` on a driven vehicle. This extends the ceiling in ADR-017 to land.

6. The `enginePower` unit resolution. The BIKI states `enginePower` is in kW. An earlier note in `docs/wiki/research/soil-strength-nrmm.md` calls it a unitless PhysX tuning value. The plan resolves this by inspection of the shipped config and the engine before any mapping of `net_power_kw` onto `enginePower`. Until the probe confirms the unit and the drivability, no `enginePower` key is emitted.

7. The licence rule. The reference mods and RHS, CUP and DCS are structure-only. No number is copied from a No-Derivatives source. Every number comes from a primary published source: a flight manual, a pilot's operating handbook, a type certificate data sheet, a standard or a maker datasheet. A proprietary or unheld document is a lead, not a value source.

8. The catalogue expansion and the `no_source` rule. Every air class is matched to a real type with a sourced spec, or recorded as `no_source` with a reason. No analogue is invented. The coverage artefact reports the target.

9. The shared-foundation decision for land vehicles. The systems specification is one foundation for two families. The land family reuses the contract, the match resolver, the source tooling, the config projection and the kernel shape. It is a branch, not a rewrite.

## Alternatives rejected

- A single widened flight-model row. Rejected: the four-value row is pinned by a test and the pure kernel `fnc_calculateAirEngineLoad.sqf` stays a pure power model. The systems fields get a separate lookup.
- A new PBO. Rejected: no new engine code is needed. The corpus projects into the existing mobility addon, exactly as the vehicle corpus does.
- A runtime flight-model swap. Rejected: the engine resolves the flight dynamics model at config load. There is no `setFlightModel` and no per-object model flag.
- An engine XML for land. Rejected: the engine reads no XML for a carx, tankx or shipx vehicle. The load-time `CfgVehicles` block is the consumer.

## Consequences

- The systems fields feed the runtime layer through one row and one per-frame driver.
- A class with no held value emits no load-time key, so the corpus never sets a wrong spec for everyone in the session.
- The scripted magnitude is a residual the operator signs. It is not a gate.
- The four-value row and the pure kernel `fnc_calculateAirEngineLoad.sqf` are unchanged.
- No new PBO, no runtime model swap and no land engine XML ship.

## References

- `data/vehicle/SCHEMA.md`, sections 16 and 17.
- `data/aircraft/SCHEMA.md`, section 10.
- `docs/adr/ADR-017-flight-physics-ceiling.md`, the flight physics ceiling.
- `docs/adr/ADR-018-aircraft-catalogue.md`, the aircraft catalogue.
- `tools/validation/gen_physics_config.py`, the one `CfgVehicles` block.
- `tools/validation/gen_aircraft_systems.py`, the systems lookup.
- `docs/architecture/vehicle-systems-pipeline.md`, the shared pieces and the land branch points.
