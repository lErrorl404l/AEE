# Mass gap source plan

This document records the three remaining mass gaps in the AEE engine
surface. Each gap names the engine key, the held-data status, the source
class to seek and the licence. The document invents no figure. No gap ships
today, because no figure is held for any of them.

## (a) Cargo and ammo boxes

- Engine key: the top-level `CfgVehicles` `mass` key on a static box class
  and on an ammo box class.
- Held data: none. No box tare mass is held.
- Source class to seek: a maker datasheet or an army datasheet that states
  the box tare mass, that is the empty box mass.
- Licence: public domain or maker.
- Nearest held analogue: the MK19 40 mm 32-round container at 19050.9 g in
  `data/ballistics/sources/magazine_mass.json`. It is a loaded mass, not a
  box tare mass, so it is a lead and not a value.

## (b) Mortar bombs

- Engine keys: `CfgMagazines >> mass` and the `CfgAmmo` mass.
- Held data: none. No mortar bomb mass is held.
- Source class to seek: a US Army technical manual or field manual that
  states the mortar bomb mass.
- Licence: public domain.

## (c) Launcher empty masses

- Engine key: `CfgWeapons >> ItemInfo >> mass`.
- Held data: none for a launcher tube. The nearest held proxy is the Javelin
  Command Launch Unit at 7.0 kg in
  `data/equipment/sources/device_mass.json`. The proxy is the sight unit and
  not the launcher tube, so it is a lead and not a value.
- Source class to seek: a maker datasheet that states the launcher tube
  empty mass.
- Licence: public domain or maker.

## Summary

| Gap | Engine key | Held data | Source class to seek | Licence |
|---|---|---|---|---|
| Cargo and ammo boxes | `CfgVehicles >> mass` | none | a maker or army datasheet for the box tare mass | public domain or maker |
| Mortar bombs | `CfgMagazines >> mass` and `CfgAmmo mass` | none | a US Army technical manual or field manual for the mortar bomb mass | public domain |
| Launcher empty masses | `CfgWeapons >> ItemInfo >> mass` | none | a maker datasheet for the launcher tube empty mass | public domain or maker |

## Licence rule

Every figure AEE uses comes from a held public-domain, maker or CC-BY-SA
source. AEE uses no value from RHS, CUP, the Hatchet H-60, BradMick HeliSim
or DCS.
