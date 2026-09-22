# ADR-004: Recoil and Item Mass Placement

Status: Accepted
Date: 2026-09-22
Decision: Recoil physics lives in ballistics. The shooter's response and
the carried-load model live in physiology. A weapon's mass and a load's
propellant charge are researched reference data, held like every other
value in this project: a source, a grade, and a unit.

## Context

[ADR-003](ADR-003-verified-ballistics-data.md) settles how a ballistic
value enters the database. Recoil and item mass needed the same treatment,
because they span two addons and two physical questions.

Free recoil is momentum conservation. The recoiling momentum equals the
ejecta momentum plus the propellant gas momentum, and the gas velocity is
a multiple of the muzzle velocity. That is interior ballistics, the same
family as the muzzle velocity and the spin rate already computed in
`aee_ballistics`. The human response to that impulse, and the mass a
soldier carries, are human factors.

The source is the SAAMI Gun Recoil Formulae. It states the relations, the
gas factor by arm type (1.75 rifle, 1.50 shotgun or pistol, 1.25 long
shotgun), and a worked example: a 3.175 kg shotgun firing 38.22 g of
ejecta at 388.6 m/s with a 2.165 g charge returns 30.22 ft-lb.

The project already holds an equipment library for clothing, armour and
load carriage (`docs/wiki/research/equipment-library.md`), classified by
classname family keywords and consumed by the stamina model. It holds no
weapon.

## Decision

1. `aee_ballistics_fnc_calculateRecoil` computes the impulse, the recoil
   velocity and the free recoil energy. It takes the ejecta mass, the
   muzzle velocity, the charge mass, the firearm mass and the arm type.
   The arm type follows the cartridge classification, so the caller does
   not supply it.
2. The shooter's response belongs to physiology, which consumes the
   impulse. It reads the value through a guarded call and falls back
   locally, so physiology works when ballistics is absent.
3. A weapon's mass is a value on the weapon record (`mass_kg`), and a
   load's propellant charge is a value on the load record
   (`charge_mass_g`, with `charge_kind` naming a service charge or a
   reloading charge). Both enter with a source and a grade.
4. A service charge is preferred. A reloading charge is a marked weaker
   grade, because it is a handload for that bullet and not the factory
   charge.
5. An archived manual supplies a value only after a person reads the
   verbatim line. Mined rows are candidates, and the file name says so
   (`weapon_mass_candidates.json`). The merge step reads only
   `weapon_mass.json` and `weapon_mass_manuals.json`.
6. A weapon whose mass is not held returns no recoil value. A family
   keyword fallback is allowed for the carried load, and the fallback is
   labelled as such.

## Consequences

- The physics is verifiable against the standard's own worked example.
  Docker phase 55 holds it: the SQF returns 30.161 ft-lb against the
  printed 30.22.
- The gas term is about 8 percent of the impulse, so a charge error of
  20 percent moves free recoil energy by under 2 percent. A charge is
  therefore worth researching, but it is not the sensitive term.
- A weapon with no held mass cannot report recoil, and the model says so
  rather than inventing a number.
- The next data captures are the loaded magazine mass and the general
  kit mass, because the carried load drives the stamina and the thermal
  models.
