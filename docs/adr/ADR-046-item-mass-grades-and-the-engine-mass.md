# ADR-046: Item-Mass Grades and the Engine Mass

Status: Accepted
Date: 2026-10-23
Decision: The item-mass resolver states one grade with every answer, and the
engine config mass is the last figure before zero. The engine mass ships as
grade `engine_mass` and is never presented as a published figure.

## Context

`aee_clothing_fnc_getItemMass` resolves a carried item to kilograms. The
resolver is generated from the research captures under
`data/equipment/sources/` (ADR-004, ADR-005). A capture names a family
keyword and the table holds the published median mass for that family and
category.

An item with no capture and no family keyword fell to the type rung and
returned 0 kg. A retextured uniform is the live case: it names no product
family, so it weighed nothing in play. The class still declares the
engine's own config mass, and that key was already read in this area as an
identity signal for the band fallback.

ADR-003 sets the value grades for research. That vocabulary does not cover
a runtime answer, so the resolver had no way to say what it had returned.

## Decision

1. The resolver resolves in this order. It returns the first figure it can
   name.
   - `sourced`: the classname names a researched family, and the figure is
     that family's published mass.
   - `family`: a published family mass the class does not name. The nearest
     ancestor names the family, or the band selects one from the engine
     mass. The trace states the family that answered.
   - `engine_mass`: no published figure exists, and the class declares an
     engine config mass. The answer is the engine value in kilograms.
   - `type`: no published figure and no engine mass. The caller's slot
     names the kind of item, the trace states that kind, and the mass is 0.
   - `zero`: nothing is known about the item. The mass is 0, labelled as
     zero.
2. The engine mass is the engine's value. The config key is in 0.1 lb
   units and the resolver converts it with `ENGINE_MASS_UNIT_KG`. The
   figure is never written to a capture, a catalogue or a coverage table,
   and its grade states that the engine supplied it.
3. The band fallback stays. It selects a PUBLISHED family mass by the
   engine mass, so a band answer is grade `family` and never
   `engine_mass`.
4. A class with no engine mass still returns 0, labelled.

## Consequences

- A carried item with a declared config mass now weighs something in play.
  The value is the engine's figure and the trace says so.
- No research value and no generated table row changes. Only the last rung
  of the resolver changes.
- `tools/tests/test_inventory_load.py` runs the resolver and proves the
  rung order, so a later edit cannot promote the engine mass above a
  published one.
- The engine mass is a value of the installed game config, so it may change
  with a game patch. The grade makes that visible rather than silent.

## References

- ADR-003, the research value grades and source hierarchy.
- ADR-004, recoil and item mass.
- ADR-005, the carried load and item mass.
- ADR-037, the PhysX mass surface and the build-time grade gate.
