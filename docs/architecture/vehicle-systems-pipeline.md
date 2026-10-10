# The shared vehicle systems pipeline

The systems pipeline is one foundation for two vehicle families. The aircraft
family is the first consumer. The land family is a branch, not a rewrite. The
branch reuses every shared piece and adds no second copy.

The corpus contracts themselves live in `data/vehicle/SCHEMA.md` and
`data/aircraft/SCHEMA.md`. This note names the pieces and the branch points.
It repeats no contract.

## The shared pieces

These pieces are family-agnostic. One name for one thing.

- The shared systems field contract. `data/vehicle/SCHEMA.md` section 16
  defines the fuel, engine, mass, damage and status fields. Each field
  carries a unit, a source class, a published flag and an engine hook or a
  marker.
- The land physics surface. `data/vehicle/SCHEMA.md` section 17 defines the
  carx, tankx and shipx `CfgVehicles` surface. Each field is published,
  derived or engine schema.
- The match resolver. The five-layer ladder and the class binding resolve
  one game class to one real-world entry. The loader
  `tools/validation/vehicle_catalogue.py` holds the resolver and the field
  registry.
- The source-fetch and verify tooling. `tools/validation/fetch_vehicle_sources.py`
  holds one source document and checks its digest. The validator
  `tools/validation/validate_aircraft_data.py` is the provenance gate over
  the corpus.
- The coverage generator. `tools/validation/gen_aircraft_coverage.py` gives
  every class token and every roster class one state. A class with no real
  counterpart is recorded as `no_source`.
- The load-time config projection. `tools/validation/gen_physics_config.py`
  is the sole owner of the one `CfgVehicles` block. One build-time predicate
  governs every emitted key.
- The systems kernels. The fuel, engine, damage and status kernels run under
  one per-frame driver. A kernel reads the systems row and never reads a
  config value at runtime.

## Where the land branch consumes it

The land family reaches the shared pieces at these points. The list states
the intended branch, not a finished state.

- The same shared contract. A land vehicle reads the shared systems fields
  in `data/vehicle/SCHEMA.md`. The contract needs no change for the branch.
- A land-vehicle class binding. A land class binds to a real-world entry in
  `data/vehicle/class_bindings.json`, as an air class does.
- A land-vehicle catalogue under `data/vehicle/`. A land entry lives in
  `data/vehicle/catalogue/` and carries the same value object and grades.
- The same config projection block. The land keys join the one `CfgVehicles`
  block under the same build-time predicate. The block count stays one.
- The same kernel shape. A land kernel takes the same systems row and the
  same per-frame driver shape as an aircraft kernel.

## The no-XML decision

A land vehicle uses no engine XML. The engine reads no XML for a carx, tankx
or shipx vehicle. The land branch therefore consumes the shared spec through
the load-time `CfgVehicles` physics block. It does not add a second data
path.

## The engine-owned anchors

Some land behaviour is engine-owned. AEE does not replace it. The tyre and
contact solver, the gearbox shift logic, the suspension and the engine-power
curve stay with the engine. AEE owns only bounded force deltas on the owner
machine. AEE never calls `setVelocity` on a driven vehicle. This extends the
ceiling in ADR-017 to land.

## The first consumer and the branch

The aircraft family is the first consumer. It proves the schema, the
resolver, the tooling, the projection and the kernels end to end. The land
family then branches from that proven path. The branch adds a catalogue, a
binding and a projection section. It rewrites no shared piece.
