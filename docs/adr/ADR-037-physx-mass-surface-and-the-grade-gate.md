# ADR-037: PhysX Mass Surface and the Grade Gate

Status: Accepted
Date: 2026-10-10
Decision: AEE ships the magazine loaded mass as an engine key, calibrates the
land vehicle mass, and gates the remaining physics keys at build time. AEE
gives no mass to a person, to a ragdoll, to terrain or to the flight model.

## Context

A mass is the deepest physical quantity the engine will accept. The engine
reads a mass from a small set of config keys, and each key has a different
reach. Some keys are plain scalars with no gate. Some keys are gated by a
two-grade rule. Some surfaces carry no mass at all.

The magazine is the heaviest repeated item a soldier carries, and the engine
reads `CfgMagazines >> mass` as the magazine PhysX mass. The magazine corpus
holds 76 published magazine masses and 12 round masses. The mass is a held
value or a value derived from the held empty mass and the held round mass.

The land vehicle mass is a calibrated scale of a held real mass. The operator
approved the calibration on 2026-10-01. The 18 land classes carry the
grandfathered `maxSpeed` and `mass` block.

The land carx, tankx and shipx physics keys and the aircraft keys are
identity-derived. A key is emitted only when the class identity grade and the
held value grade are both `documented`. Every current identity is `claimed`.

The character controller, terrain and the flight model are closed. The
runtime hook `setMass` acts on a PhysX object, not on the character
controller. A surface carries friction and no mass key. The engine resolves
the flight dynamics model at config load (ADR-017).

## Decision

1. `CfgMagazines >> mass` ships the magazine LOADED mass in kg. The loaded
   mass is the held value, or DERIVED as `empty_mass_g + capacity *
   round_mass_g` from the held round mass for the chambering. The key is NOT
   gated on the CfgVehicles predicate. A magazine that resolves no mass is a
   lead and is not emitted.

2. A magazine is weighed loaded, not empty. The loaded basis is the real
   carried weight. The empty mass stays the load-model input.

3. The land `CfgVehicles >> mass` is a calibrated scale of a held real mass,
   `mass = real_analogue_mass_kg / fit.scale`. The block is un-gated and
   grandfathered. The 18 emitted bodies are frozen.

4. The land carx, tankx and shipx physics keys and the aircraft keys are gated
   at build time by `emit_key`. The predicate ships a key only when the class
   identity grade and the held value grade are both `documented`. Config is
   load-time and global, so the build-time predicate is the only gate.

5. AEE gives no mass to a person and no mass to a ragdoll. AEE gives no mass
   to terrain. AEE runs no runtime flight-model swap and no blade-element
   replacement. The three closed surfaces are stated in
   `docs/wiki/research/physx-mass-surface.md`.

6. Every figure comes from a held public-domain, maker or CC-BY-SA source.
   AEE uses no value from RHS, CUP, the Hatchet H-60, BradMick HeliSim or
   DCS.

## Consequences

- The engine carries the real magazine weight through its own PhysX mass. The
  thermal loadout consumer reads a non-zero magazine content mass.
- The land physics surface and the aircraft keys ship no key while every
  identity is `claimed`. That is the gate working, not a defect.
- The ship `mass` waits on a held displacement. The cargo, mortar and
  launcher gaps each wait on a held source. The gaps are recorded in
  `docs/wiki/research/ship-mass-source-plan.md` and
  `docs/wiki/research/mass-gap-source-plan.md`.
- A fictional Arma class binds to a real analogue only at grade `claimed`.
  A `documented` link needs a held tier 2 or tier 3 source that names the
  link.

## References

- ADR-002 (facts only) and ADR-003 (the source hierarchy and the grades).
- ADR-017 (the flight physics ceiling and the runtime hooks).
- `docs/wiki/research/physx-mass-surface.md` (the surface map).
- `tools/validation/gen_engine_overrides.py` and
  `tools/validation/gen_physics_config.py` (the generators).
