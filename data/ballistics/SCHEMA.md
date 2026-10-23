# Ballistics data schema

The full schema and its source hierarchy are in
[ADR-003](../../docs/adr/ADR-003-verified-ballistics-data.md). This file
states the record kinds and the rules the gate enforces. The gate is
`tools/validation/validate_ballistics_data.py`.

## Record kinds

| Kind | Key | Holds |
|---|---|---|
| cartridge | `cartridge_id` | a chambering: dimensions, pressure, reference twist |
| projectile | `projectile_id` | a bullet: mass, diameter, length, ballistic coefficient |
| load | `load_id` | a cartridge and projectile pair: velocity anchors, service velocity |
| weapon | `weapon_id` | a launcher or small arm: mass, twist, chambering |
| source | `source_id` | a cited standard, manual, measurement or maker page |

Every value is an object with `value`, `source` and `grade`. A value with
a dimension also carries `unit`.

## Weapon kind

A weapon record has an optional `kind`. A small arm leaves it absent. The
two marked kinds are:

- `launcher`: fires a rocket or a recoilless round. It has no rifled
  barrel, so it holds no twist, and it chambers no cartridge.
- `crew_served`: a gun that a crew serves and a soldier does not carry.

### The launcher rule

A launcher chambers no cartridge. It names the round it fires in a
`rocket` value:

```json
{
 "weapon_id": "rpg7",
 "kind": "launcher",
 "cartridge_id": "",
 "values": {
  "rocket": {"value": "PG-7V", "unit": "name", "source": "wikipedia_rpg7", "grade": "claimed"},
  "mass_kg": {"value": 6.3, "unit": "kg", "source": "wikipedia_rpg7", "grade": "claimed"}
 }
}
```

The gate rejects a launcher that carries a `cartridge` value or a
`cartridge_id`, and a launcher that names no rocket. A launcher is
exempt from the chambering-gap rule, which applies to every other weapon.

## Ballistic coefficient

A projectile holds `bc_g1` or `bc_g7`, never a converted value. Each
coefficient names its drag model in the field name. The source states
whether the value is a measurement or a maker claim, and the gate grades
it from that source.

## Form-factor review

The independent verifier screens every G7 record against a form-factor band
derived from the corpus, and flags a record outside the band. A flag is a
question for a person, and `form_factor_review` records the answer:

```json
"form_factor_review": {
 "decision": "genuine",
 "reason": "Berger states this G7 coefficient and its own G7 form factor of 0.976 for the same bullet; the form factor of 0.978 below the band is the bullet's long ogive and is not a coefficient fault.",
 "evidence": ["berger_bullets"],
 "reviewed": "2026-10-23"
}
```

The decision is one of `genuine`, `source_error`, `unit_error` or
`unsupported`. Only `genuine` leaves the record outside the band. The other
three say the value was corrected or withdrawn, so the record must leave the
flag list, and the verifier reports a review that did not. `evidence` names
the sources that state the value, and the data gate rejects an entry whose
evidence is empty or names an unknown source. Reviews are written in
`data/ballistics/form_factor_reviews.json` and copied onto the record by
`gen_projectiles.py`, so a rebuild cannot lose them.
