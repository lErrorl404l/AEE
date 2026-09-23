# ADR-005: The Carried Load and the Item-Mass Ladder

Status: Accepted
Date: 2026-09-23
Decision: The carried load sums four resolvers, and each item is weighed by
exactly one of them. An item mass comes from a research capture when one is
held, from a family tier otherwise, and from the item's own model only as a
recorded derived value. The engine `load` command is a capacity ratio, not a
mass, and engine config `mass` is identity evidence only.

## Context

ADR-004 places the carried-load model in physiology and settles how a
weapon mass enters the database. It leaves three questions open.

1. The library weighed the worn slots and the pack contents through the
   engine `load` command. That command returns 0..1 of the container
   capacity, so the combined load added a fraction as if it were kg. The
   fault hid in plain sight, because the number is small and plausible.
2. The library held no inventory items at all. A soldier's NVG, radio,
   GPS, medical kit and weapon attachments were absent from the load.
3. A mod item with no capture resolved to nothing, and the obvious cheap
   substitute (engine config `mass`) is barred by ADR-003 tier 6: mod and
   engine config values are identity signals, never value sources.

ADR-001 supplies the missing method. The engine exposes an item's real
geometry, and `fnc_measureBarrel` already measures a weapon from its own
model under that principle.

## Decision

1. The carried load is the sum of four resolvers, and each item is counted
   by one of them:
   - the worn slots (uniform, vest, headgear, goggles, backpack)
   - the carried weapons
   - the magazines and their rounds
   - the inventory walk: container contents, assigned slot items (map,
     compass, watch, GPS, radio, NVG, binocular) and weapon attachments

   The walk skips the worn slots, the carried weapons and the magazines.
   Docker phase 58 proves the two engine facts the walk needs: `items` and
   `assignedItems` do not overlap, and each item reaches the walk once.

2. The engine `load` command never supplies a mass. It returns a 0..1
   capacity ratio. The pack contents are weighed item by item instead.

3. Item mass follows a ladder, and a lower rung never displaces a higher
   one:
   - **Found**: a cited research capture (schema:
     `data/equipment/SCHEMA.md`), projected by
     `tools/validation/gen_equipment_data.py`
   - **Family tier**: the researched family keyword value
   - **Derived**: the item's own model, envelope volume x a calibrated
     effective density. Grade Derived (ADR-003), formula and inputs
     recorded
   - **Unknown**: 0. The item is not guessed, and the coverage test
     reports it

4. A mod or engine config `mass` is identity evidence only (ADR-003 tier
   6). It never supplies a kilogram value.

5. A rucksack capture states the mass of the EMPTY pack, because the walk
   weighs the contents. The generator projects nothing else.

6. The derived rung is enabled only after calibration against researched
   masses. Until then an item with no capture and no family returns 0.

## Consequences

- The load is complete: the heaviest single item (the weapon), the
  repeated item (the magazine) and the small kit all enter, and a double
  count is a test failure rather than a silent error.
- An engine semantic is verified in the engine, not assumed. The docker
  probe is the gate, because HEMTT cannot see a runtime type error (see
  GAP-012 and GAP-014 in `docs/gaps-register.md`).
- Coverage is measurable. A capture that lands without a regenerated
  resolver fails `test_inventory_load.py`.
- The derived rung is intentionally absent, not silently guessed. It needs
  a measured calibration set, which the captures now supply.
- The model still omits items the engine does not expose (a weapon stowed
  in a container is weighed, its loaded magazine is weighed, but a mod
  that hides mass in an unrelated config field is not).

## References

- ADR-001 engine anchors, the measure-from-model principle
- ADR-003 the four value grades and source hierarchy
- ADR-004 the placement of recoil and item mass
- `data/equipment/SCHEMA.md` the capture schema
- `docs/wiki/research/equipment-library.md` the equipment research
