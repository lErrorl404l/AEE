# ADR-017: Flight Physics Ceiling and Runtime Aircraft Forces

Status: Accepted
Date: 2026-10-05
Decision: The flight model is a load-time config choice. AEE layers bounded runtime forces on top of it. The scripted layer fixes the advanced-model gate, runs turbulence as a local addForce and addTorque, and feeds air density and icing into lift, drag and mass.

## Context

Research into the Arma 3 flight models found a defect and a ceiling.

The defect. `fnc_applyFlightTurbulence` gated its `addForce` branch on `isClass (configOf _veh >> "AdvancedFlightModel")`. That class does not exist in vanilla, and a vanilla config has zero hits for the name. The gate matched nothing, so the branch was dead. Every aircraft, advanced-model helicopters included, took the simple-model `setVelocity` path, which is a per-frame local velocity overwrite.

The engine. The flight dynamics model is resolved at config load. There is no runtime command to switch the model, no per-object model flag, and no `setFlightModel`. Advanced-model selection is scenario global through `forceRotorLibSimulation` in `description.ext` or `server.cfg`. `difficultyEnabledRTD` reads that state. A rotor-lib airframe carries the `RotorLibHelicopterProperties` class.

The runtime hooks are `addForce`, `addTorque`, `setMass`, `setCenterOfMass`, `setVelocity`, `setVectorDirAndUp`, `flyInHeight` and the wind commands. There is no per-tick force accumulator. `addForce` acts on a PhysX object and clears after the step, so a layer calls it every tick. `setVelocity` is a local per-frame velocity overwrite and is not multiple-player safe when a non-owning machine calls it.

The unused state. AEE computed the air density (`aee_core_currentAirDensity`), the lift ratio (`aee_mobility_currentLiftRatio`), and the FAR 25 Appendix C icing state (`aee_atmos_airframeIcing`, `aee_atmos_iceAccretion_kg`). Only turbulence read the density, and no flight path read the icing state at all.

## Decision

1. The advanced-model gate is `difficultyEnabledRTD`, or the `RotorLibHelicopterProperties` class for a rotary airframe. The pure kernel `fnc_resolveFlightModel` is the executable truth table over the two booleans. The bogus class test is removed.

2. Turbulence is a physical layer. An advanced-model or rotor-lib airframe receives a bounded `addForce` from `fnc_calculateTurbulenceForce`, plus a bounded `addTorque` nudge on a rotary airframe. The force is aerodynamic and mass-aware: the dynamic pressure times the airframe's effective drag area, `F = 0.5 rho v^2 (Cd S)`, read from the aircraft corpus record. The force carries no mass, so the acceleration it realises is `F / mass`: a heavy airframe resists a gust and a light one is nudged. The simple model cannot integrate a PhysX force, so it takes the same acceleration as a local velocity delta and is weight-aware too. Each application is gated to the machine that owns the object, so it is multiple-player safe and it never double-applies on a dedicated server.

3. Air density and icing are consumed in flight. The pure kernel `fnc_calculateAeroPenalty` turns the lift ratio and the icing severity into a bounded lift loss and drag rise. `fnc_applyAirframeLoad` applies the lift loss as a downward `addForce`, the drag rise as an `addForce` opposing the velocity, and the ice mass as a `setMass` delta. The combined lift loss is capped, so the layer can never stall the airframe.

4. The FDM is a load-time limit. AEE does not attempt a runtime flight-model swap and does not ship a blade-element replacement. A mission that wants the advanced model sets `forceRotorLibSimulation` and supplies a replacement config or a rotor-lib XML. That is a separate load-time change.

5. The realistic ceiling is stated. Arma 3 cannot become DCS. The engine offers a fixed set of runtime force hooks and a load-time config model. The scripted layer adds turbulence, density and icing effects. It cannot replace the aerodynamics solver.

## Consequences

- The advanced-model branch runs for the first time. Advanced-model helicopters and fixed-wing aircraft take a force, not a velocity overwrite.
- The density and icing state now changes flight behaviour.
- The turbulence force is aerodynamic and sourced. The unsourced divisor (100) is removed. The drag area is the record's `drag_area_m2` (Cd S, fixed-wing, `data/aircraft/SCHEMA.md` section 5) or `rotor_disc_area_m2` (the rotor disc, rotary-wing), and the kernel default 0.7 m2 stands when neither is held. The remaining UNSOURCED magnitudes are the turbulence force cap (0.25 of weight), the turbulence torque fraction (0.05), the density lift-loss maximum (0.6), the icing lift-loss maximum (0.35), the icing drag-rise maximum (0.5) and the combined lift-loss cap (0.45). Each is bounded and pinned by a test.
- The ice mass is one global atmos value applied to every local airframe in range. That is an approximation, not a per-airframe accretion.
- The turbulence and the airframe load are client effects. A dedicated server does not run them, so a server-owned AI airframe receives no scripted turbulence.
- Alternatives: a runtime FDM swap was rejected because the engine resolves the FDM at config load. A blade-element replacement was rejected for the same reason.

## References

- `addons/flight/functions/fnc_applyFlightTurbulence.sqf`, the gate and the physical layer.
- `addons/flight/functions/fnc_calculateTurbulenceForce.sqf`, the aerodynamic gust force.
- `addons/flight/functions/fnc_resolveTurbulenceArea.sqf`, the drag area from the corpus row.
- `addons/flight/functions/fnc_applyAirframeLoad.sqf`, the density and icing consumer.
- `addons/mobility/script_component.hpp`, the bounded constants.
- `data/aircraft/SCHEMA.md`, the drag area and rotor disc area derivations.
- FAR 25 Appendix C, the airframe icing envelope.
- ISO 2533, the standard atmosphere.
- `docs/adr/ADR-001-engine-anchors.md`, the verify-against-the-engine rule.
