# Ship mass source plan

This document records the ship mass gap and the public documents that can
close it. The ship has no mass today. The document names the exact source
documents and their licence. It invents no displacement.

## The gap

The engine ship mass is the top-level `CfgVehicles` `mass` key. The engine
has no separate `shipx` mass key. The `shipx` block is the ship physics
surface, and `data/vehicle/SCHEMA.md` section 17 holds its field table.

No displacement and no hull mass is held. The catalogue holds no ship entry,
and no class binding names a ship class. A ship binding needs a held
displacement before the generator can emit its `mass` key.

The surface is gated. The generator admits a land surface key only when the
class identity grade and the held value grade are both `documented`. The
predicate is `emit_key` at `tools/validation/gen_physics_config.py:399`.
Every identity is `claimed` today, so the generator emits nothing.

## The two displacement states

The schema names two held states for the one engine key.

| Schema field | State |
|---|---|
| `displacement_kg` | displacement, light ship |
| `full_load_displacement_kg` | full load displacement |

Both carry the unit kg. The light ship displacement is the empty hull
displacement. The full load displacement adds the crew, the fuel, the
ammunition and the stores.

## The documents to seek

Each document below publishes a ship displacement. Each entry names the
figure it publishes and its licence.

| Document | Figure published | Licence |
|---|---|---|
| US Navy, Naval Sea Systems Command (NAVSEA), Naval Vessel Register (NVR), `nvr.navy.mil` | Displacement, light and full load, for each US Navy hull | Public domain. A US Government work is not subject to copyright (17 U.S.C. 105). |
| US Department of Transportation, Maritime Administration (MARAD), Vessel History Database, `vesselhistory.marad.dot.gov` | Vessel characteristics, including displacement and deadweight, for each recorded vessel | Public domain. A US Government work is not subject to copyright (17 U.S.C. 105). |
| US Army and US Navy watercraft technical manuals, the TM 55-19xx series | Light ship and full load displacement for Army watercraft and small craft | Public domain. A US Government work is not subject to copyright (17 U.S.C. 105). |
| Wikipedia ship class articles | Displacement, light and full load, as published for the class | Creative Commons Attribution-ShareAlike 4.0 (CC BY-SA 4.0). |

The Naval Vessel Register is the primary Navy source. The MARAD Vessel
History Database is the primary merchant source. The watercraft technical
manuals are the primary Army source. A Wikipedia class article is a tier 5
compilation and is a fallback only.

## The lead

The ship mass is a lead. No displacement is held today, so nothing ships.
The first source that resolves is the Naval Vessel Register for a Navy hull,
or a watercraft technical manual for an Army craft. A held figure enters the
catalogue first, with its unit, source, locator and grade. The binding and
the calibration row follow. The `mass` key ships only after both grades are
`documented`.

## Licence rule

Every figure AEE uses comes from a held public-domain, maker or CC-BY-SA
source. AEE uses no value from RHS, CUP, the Hatchet H-60, BradMick HeliSim
or DCS.
