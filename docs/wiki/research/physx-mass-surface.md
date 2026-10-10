# PhysX mass surface and the AEE ceiling

This document maps every engine surface that carries a mass, the reach AEE has
over each one, and the surfaces AEE cannot reach. Each reachable surface names
a `file:line` citation. Each unreachable surface names the reason.

## Reachable surfaces

| Surface | Reach | Citation |
|---|---|---|
| `CfgMagazines >> mass` | Shipped. The loaded mass of the magazine, consumed by the load model and the engine `getMass`. | Emit `tools/validation/gen_engine_overrides.py:804`, consume `addons/thermal/functions/display/fnc_calculateUnitLoadoutThermal.sqf:70`, engine `addons/core/functions/fnc_handleCollisionDamage.sqf:56` |
| `CfgVehicles >> mass` | Shipped. The calibrated land mass of the vehicle, consumed by the engine `getMass`. | Emit `tools/validation/gen_physics_config.py:746`, consume `addons/mobility/functions/fnc_applyRollover.sqf:144` |
| `CfgWeapons >> ItemInfo >> mass` | Shipped. The carried item mass, consumed by the load model. | Consume `addons/thermal/functions/display/fnc_calculateUnitLoadoutThermal.sqf:48` |
| `CfgWeapons >> WeaponSlotsInfo >> mass` | Shipped. The carried weapon mass, consumed by the load model. | Consume `addons/thermal/functions/display/fnc_calculateUnitLoadoutThermal.sqf:90` |
| `CfgVehicles >> carx`, `tankx` and `shipx` physics keys | Mapped. The generator holds the surface fields, and the build-time gate emits them. | Fields `tools/validation/gen_physics_config.py:184`, schema `data/vehicle/SCHEMA.md:703` |

## Gated surfaces

The land `carx`, `tankx` and `shipx` physics surface and the aircraft keys are
gated at build time. The predicate `emit_key` ships a key only when the class
identity grade and the held value grade are both `documented`. The predicate
lives at `tools/validation/gen_physics_config.py:399`. Every current identity
is `claimed`, so production ships no gated key. The gate is the working state,
not a defect. The ship surface has no held displacement, so the `shipx` mass
waits on a source.

## Out of reach

- The character controller. AEE cannot give a person or a ragdoll a PhysX
  mass. The runtime hook `setMass` acts on a PhysX object, not on the
  character controller. AEE therefore gives no mass to a person and no mass
  to a ragdoll. Citation `docs/adr/ADR-017-flight-physics-ceiling.md:15`.
- Terrain and `CfgSurfaces`. A surface carries friction and no mass key, so
  AEE gives terrain no mass. Citation `data/engine/verdicts.json:178`.
- The flight model. The engine resolves the flight dynamics model at config
  load. AEE runs no runtime flight model swap and no blade-element
  replacement. Citation `docs/adr/ADR-017-flight-physics-ceiling.md:29`.

## Licence rule

Every figure AEE uses comes from a held public-domain, maker or CC-BY-SA
source. The sources are the US technical manuals and field manuals, the maker
datasheets and manuals, and the NATO and SAAMI standards. AEE uses no value
from RHS, CUP, the Hatchet H-60, BradMick HeliSim or DCS.
