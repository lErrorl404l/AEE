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
