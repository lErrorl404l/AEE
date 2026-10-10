# ADR-042: Ground-Vehicle Fuel Consumption and Coolant Thermal Management

Status: Accepted
Date: 2026-10-10
Decision: AEE models ground-vehicle fuel consumption from the road-load
equation and a brake-specific fuel consumption scalar, and models the coolant
temperature from the heat that consumption rejects. The model reuses the
repository's existing SFC relation and its existing convection and
first-order-lag form. The engine owns the tank: the model publishes the
consumption, the range and the coolant derate, and never calls `setFuel`.

## Context

The engine burns ground-vehicle fuel at its own config `fuelConsumptionRate`,
which is not the brake-specific consumption a real engine map gives. Two
sibling models already exist. The flight addon
(`aee_flight_fnc_calculateFuelBurn`) converts a specific fuel consumption to a
mass rate and burns a scripted tank. The thermal addon
(`aee_thermal_fnc_calculateVehicleHeat`) solves a lumped-capacitance engine
body temperature with the Holman flat-plate air correlation and an exact
exponential step.

Issue #111 asks for ground-vehicle consumption from the road-load equation and
a brake-specific fuel consumption scalar, a terrain multiplier, a slip loss,
and a coolant thermal limit with a power derate. The brief states the values
and names its sources: Gillespie for the road-load anchors, Heywood for the
BSFC maps and the fuel properties, SAE J1349 for the density correction the
existing power model already cites, and FM 4-01.41 for the military
consumption anchors.

The corpus holds no per-vehicle engine class, no per-vehicle rolling
coefficient and no per-vehicle idle rate. A per-vehicle value that the corpus
does not hold may not be invented.

## Decision

1. The fuel and coolant constants live in one corpus,
   `data/physics/fuel.json` (schema `aee.physics.fuel/1`). Each value carries a
   source id that resolves in the file's own source array, or a named
   derivation. The generator `tools/gen_fuel_data.py` projects the corpus to
   `addons/vehicles/functions/fnc_getFuelData.sqf`, and the validator
   `tools/validation/validate_fuel_data.py` gates it. The runtime reads the
   generated table, never the corpus.

2. Four pure kernels carry the physics. `fnc_calculateRoadLoad` is the
   road-load equation (Gillespie). `fnc_calculateFuelRate` is the brake-specific
   fuel consumption relation, the ground sibling of the flight SFC kernel.
   `fnc_calculateCoolantTemperature` is the same first-order lag and exact
   exponential step the thermal body model integrates, with the same Holman
   convection correlation. `fnc_calculateCoolantDerate` maps the coolant
   temperature to a derate and a fan state.

3. The driver `fnc_updateFuelConsumption` joins the kernels. It reads the
   generated table, computes the road load, the fuel rate, the range and the
   coolant state for each nearby local ground vehicle, and publishes them on the
   vehicle. It does NOT call `setFuel`. The engine owns the tank, and a second
   burn would double-count the engine's own rate. The published state is the
   model.

4. The coolant derate multiplies the existing engine power model
   (`fnc_calculateEnginePower`). The overheat derate is the same derating
   model, extended, not a second one.

5. The rolling-resistance base is the vehicle type (tracked takes the track
   anchor, wheeled the truck anchor), scaled by the mobility ground state. The
   base is a declared corpus default, not a measured per-vehicle value.

6. The engine class is a user setting (`aee_vehicles_engineFuelClass`) with a
   documented default (diesel). The corpus holds no per-vehicle engine class,
   so a per-vehicle class would be an invented value.

## Consequences

- The model is grounded in the two reference works and the existing repository
  correlations. Every constant traces to a source or a named derivation.
- The model publishes the consumption and the range. It does not drain the
  tank. A consumer that wants to drain it reads the published rate; a future
  change that drains it must first zero the engine's own rate, as the flight
  fuel system does, to avoid a double burn.
- A part-load BSFC penalty is not modelled: the corpus holds the best-point
  scalar, and a part-load curve is a per-class calibration the corpus does not
  carry. The scalar is applied to the power demand.
- The engine exposes no per-vehicle power scalar hook, so the coolant derate is
  applied to the player-vehicle engine power model and published per vehicle
  for other consumers.

## References

- ADR-002 (facts only) and ADR-003 (the source hierarchy and the grades).
- ADR-019 (thermal realism) and ADR-033 (aircraft systems, the fuel ceiling).
- `docs/wiki/research/fuel-thermal.md` (the sources and the formulas).
- Gillespie, "Fundamentals of Vehicle Dynamics"; Heywood, "Internal Combustion
  Engine Fundamentals"; SAE J1349.
- `tools/validation/validate_fuel_data.py` and `tools/gen_fuel_data.py`.
