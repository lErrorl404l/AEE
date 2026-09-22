# ADR-003: Verified Ballistics Reference Data (real sources only)

Status: Accepted
Date: 2026-09-22
Decision: AEE resolves every weapon, cartridge and projectile to real
records held in a cited reference database. Mod data and engine config
data never supply ballistic values. They supply identity signals only.

## Context

This ADR applies the facts-only rule of [ADR-002](ADR-002-facts-only-biome.md)
to ballistics, and the engine-anchor rule of
[ADR-001](ADR-001-engine-anchors.md) to identity. AEE identifies a
weapon from engine facts. Its values come from real references.

Mod values cannot be trusted. The Project M `.300 NM` 225 grain
ELD-Match declares G1 BC 0.717. The manufacturer publishes 0.777. The
same weapon declares a twist of 1:9.3 for a bullet that needs 1:8. A
wrong value is worse than a derived value, because it looks
authoritative.

The corpus we hold is mixed. The ABE project generated `ir_ammo.tsv`
from Arma and ACE3 config dumps. `caliber_ref.tsv` has no source
column. Neither can enter the database without re-sourcing.

The requirement is: real data, verifiable, recallable, no per-mod
support, and no maintenance beyond adding sources and new rounds.

## Decision

1. **Four levels.** Calibre, cartridge, projectile and load. The table
   keys on the cartridge, never the calibre. Two cartridges can share a
   calibre and still differ, for example 5.56x45 NATO against .223
   Remington.
2. **Two tiers.** A research database holds the cited records. A
   generated runtime table holds the compact projection for Arma. The
   runtime table is never edited by hand.
3. **A value, not a row, carries the source.** A cartridge can hold a
   standard pressure and a claimed twist at the same time.
4. **One source hierarchy.** See the table below.
5. **One corroboration rule.** See below.
6. **The database records conflicts. It never averages them.**
7. **Physics validates every value.** Citations alone are not enough.
8. **Every runtime value carries a provenance key.** The recall
   function returns any value with its source.
9. **Maintenance is data entry.** A new round is a new row. A new mod
   needs no change at all.

## Source hierarchy

The workspace rules place UK MOD first and NATO second. Civil cartridge
standards carry equal weight for civil rounds.

| Tier | Source | Entry rule |
|---|---|---|
| 1 | UK MOD, NATO STANAG and AEP, CIP, SAAMI | One source defines the value |
| 2 | Military technical manuals, proof-house data | One source, cited |
| 3 | Independent measurement, Doppler, laboratory | One source with the method recorded |
| 4 | Manufacturer published data | One source, flagged as a claim |
| 5 | Secondary compilation, website | A signal only, never an entry |
| 6 | Mod or engine config dump | Never a source. Identity only |

## Confidence grades

| Grade | Meaning | Entry rule |
|---|---|---|
| Standard | A tier 1 standard defines the value | One tier 1 source |
| Verified | Two independent tier 2 or 3 sources agree inside tolerance | Two sources |
| Measured | One tier 3 measurement, method recorded | One source and method |
| Claimed | One tier 4 manufacturer value | Recorded and flagged |
| Corroborated | A tier 4 claim plus one independent tier 2 or 3 source that agrees inside tolerance | The claim and the independent source |
| Documented | A tier 2 or tier 3 source states the value | One source, cited |
| Derived | Computed from physics and cited inputs | Formula and inputs recorded |
| Unverified | No acceptable source | Quarantined, never used |

Tolerances, per field:

| Field | Tolerance for agreement |
|---|---|
| Chamber pressure | 1 percent |
| Muzzle velocity | 1 percent or 10 m/s, whichever is larger |
| Projectile mass | 0.5 percent |
| Ballistic coefficient | 2 percent |
| Twist rate | 2 percent |
| Barrel length | 0.5 mm |

**A found value beats a formula. A formula beats a guess.** Before a
value is derived, the real value is searched for in a citable source,
and a derived value never displaces a found one. Where no source holds a
value, it is computed from the bullet's real geometry with an
established published formula, and the formula and its inputs are
recorded with the value. A numeric shortcut that maps one standard onto
another is not a derivation and is not accepted: a coefficient belongs
to the standard it was measured against. Physics computed from real
measurements is truth, and it is preferred over an absent value and over
any unfounded claim.

**The drag model follows the bullet.** The standard is chosen to match
the projectile, not the convenience of the data.

| Projectile | Standard |
|---|---|
| Flat base or blunt, handgun and older hunting designs | G1 |
| Boat tail rifle and machine gun bullets | G7 |
| Long range precision and ELR designs | G7, or G8 where a G8 coefficient is held |

A coefficient is never converted between standards to fill a gap while a
real coefficient for a suitable standard is held.

## Schema

**sources**

| Field | Purpose |
|---|---|
| source_id | Stable key |
| type | standard, manual, measurement, manufacturer, compilation |
| title, edition, identifier | For example a CIP TDCC number, a SAAMI section, a TM number, a manufacturer SKU |
| locator | Page, table or section |
| published, retrieved | Dates |
| url, archive_hash | Retrieval address and content hash |
| licence | public domain or restricted, which controls redistribution |
| note | Free text |

**cartridges**

| Field | Unit | Notes |
|---|---|---|
| cartridge_id | | Canonical key |
| names | | Aliases, for example `.300 Norma Magnum`, `300NM`, `300 Norma Mag` |
| calibre_mm, bore_mm | mm | Bullet diameter and bore |
| case_length_mm | mm | Case length |
| case_capacity_h2o_gr | grain | Optional |
| max_pressure_mpa | MPa | With the pressure standard named |
| proof_pressure_mpa | MPa | The proof pressure, where a standard states it |
| pressure_standard | | CIP, SAAMI or NATO EPVAT |
| reference_barrel_mm | mm | The barrel for the reference MV |
| standard_twist_m | m per turn | The service or standard twist |
| grooves | count | Rifling groove count, where published |
| case_family | | For example Norma Magnum |

Each cartridge also carries a `classification` object for sorting and
search, with a single `classification_source`:

| Field | Purpose |
|---|---|
| cip_tab | The source table, for example Tab I rimless |
| case_type | rimless, rimmed, belted, pistol, rimfire, shot, industrial, alarm, dust shot, other, caseless |
| cartridge_type | rifle, pistol, rimfire, shotgun, industrial, alarm, caseless, other |
| origin_country | The country that submitted the cartridge |
| year_created | The year of the first CIP entry |
| value_sources | | Source and grade per field |

**projectiles**

| Field | Unit | Notes |
|---|---|---|
| projectile_id | | Canonical key |
| names | | Aliases, for example `225 ELD-M`, `225ELDM`, `Hornady 30904` |
| manufacturer, sku | | Provenance |
| mass_g | g | |
| length_mm | mm | Needed for the stability rule |
| diameter_mm | mm | |
| bc_g1, bc_g7 | | Both models where published |
| drag_model | | G1 or G7 |
| velocity_bands | m/s | Optional, for stepped BCs |
| sectional_density | | Check value |
| min_twist_m | m per turn | The manufacturer published minimum twist |
| required_twist_m | m per turn | Miller rule at the reference MV |
| value_sources | | Source and grade per field |

**loads**

| Field | Unit | Notes |
|---|---|---|
| load_id | | cartridge_id plus projectile_id |
| mv_anchors | mm, m/s | Measured pairs of barrel length and velocity |
| service_velocity_ms | m/s | The service velocity as stated |
| velocity_reference | | Where the velocity is measured, for example 78 ft from the muzzle |
| service_pressure_mpa | MPa | The service pressure limit as stated |
| pressure_reference | | The test method and the limit type |
| twist_in | inches per turn | The required barrel twist, where stated |
| cartridge | | The cartridge as named in the specification |
| projectile | | The projectile designation, where it is not held as a record |
| powder_class | | Affects temperature sensitivity |
| temperature_sensitivity | | Where measured |
| value_sources | | Source and grade per field |

**conflicts**

| Field | Purpose |
|---|---|
| entity, field | Where the conflict sits |
| value_a, source_a, value_b, source_b | The competing values |
| resolution | The value kept |
| rule_applied | The rule that decided |
| date | When the database recorded the conflict |

## Verification

1. **Unit discipline.** Every conversion is explicit and checked.
   Grains, grams, inches, millimetres, psi and MPa.
2. **Invariants.** MV rises with barrel length and saturates. Pressure
   stays inside the cartridge MAP. Twist stays inside a manufacturing
   band. BC stays inside the envelope for that calibre, mass and length.
3. **Cross-checks.** Sectional density, the Miller stability factor,
   and the MV curve against its anchors.
4. **Sample re-verification.** A tool re-checks a random sample of the
   existing corpus against its cited source, and records the error
   rate.
5. **The gate runs in CI.** A value without a source fails the build.

## Recall

Every value in the runtime table carries a provenance key. A single
function takes a weapon, cartridge or round from the game and prints
the chain: value, unit, source, locator, dates, grade and the rejected
conflicts.

## Maintenance

1. A new cartridge or projectile is a new row plus its sources. No code
   change.
2. A new mod needs no change. Resolution uses identity signals and
   physics.
3. A changed source produces a new record and a conflict entry. The
   database keeps the old record.
4. The build regenerates the runtime table. Nobody edits it by hand.

## Consequences

- Any weapon from any mod resolves with no per-mod work.
- The recall function returns any value with its source and its grade.
- The existing corpus needs re-sourcing before use.
- Runtime size stays bounded, because the projection carries only the
  values the simulation consumes.
- A wrong value cannot hide, because the gate rejects an unsourced
  value.

## Open items for sign-off

1. The confidence grades and the tolerances.
2. The source hierarchy order.
3. The name of the recall function.
4. That derived values may drive the simulation, and that the system
   flags each one.
