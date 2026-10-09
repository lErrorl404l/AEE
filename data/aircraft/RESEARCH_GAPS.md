# Aircraft corpus research gaps

This file lists what the corpus does not yet hold and the next source to try.
It is written by hand and it names a concrete next source for every gap. The
generated reports `SOURCE_GAPS.md` and `CLASS_MAPPING_GAPS.md` carry the same
gaps in table form.

## Dropped or unresolved class mappings

- `I_Plane_Fighter_04_F` (Saab JAS 39C Gripen, Jets DLC) is bound to
  `jas39c_gripen` from the Armed Assault Wiki identity lead. The class is a
  Jets DLC class, so the vanilla air config check is still pending. Next
  source: verify the class with `hemtt utils config derapify` on the
  `Air_F_Exp` or DLC addon.
- `O_Heli_Transport_02_F` (Mil Mi-26 Halo analogue) is not present in the
  deployed air config. The CSAT heavy transport classes that do exist are
  `O_Heli_Transport_04_F` and `O_Heli_Transport_04_covered_F`. Next source:
  confirm the Mi-290 Taru class name from the Helicopters DLC config and decide
  whether it maps to `mi26_halo` or needs its own entry.
- `Air` and `UAV` are token-level only. No concrete class binding names a real
  aircraft. Next source: a vanilla `Air` or `UAV` class that carries a real
  analogue.

## Wiki identity conflicts

The Armed Assault Wiki disagrees with three existing bindings. Both values are
kept in `data/aircraft/conflicts.json`. No binding changes until a tier 2 or
tier 3 source names the engine aircraft.

- `O_Plane_CAS_02_F`: corpus `su25_frogfoot`; the wiki names the To-199
  Neophron as the Yak-130.
- `C_Plane_Civil_01_F`: corpus `cessna_172_skyhawk`; the wiki names the Caesar
  BTT as the Cessna TTx.
- `O_Heli_Light_02_F`: corpus `light_utility_rotary` (Mil Mi-2); the wiki names
  the PO-30 Orca as the Ka-60 Kasatka.

## Entries that are leads

A lead holds no held runtime value and projects a labelled zero for every
runtime field. Ten entries are runtime-ready. The held-source ceiling is these
two:

- The held UH-60A operator's manual `TM 1-1520-237-10` states the rotor
  diameter and the maximum weight but no shaft horsepower, so
  `uh60a_black_hawk` stays a lead. Next source: a held engine document or a
  tier 4 manufacturer datasheet that states the T700-GE-700 rating.
- The held DTIC case history `ADA378729` states the engine model and the empty
  weight but no shaft power and no rotor diameter, so `rah66_comanche` stays a
  lead. Next source: a held rotorcraft datasheet that states the T800 rating
  and the rotor diameter.

The remaining first-slice leads are `a10a_thunderbolt_ii`, `su25_frogfoot`,
`l159_alca`, `su57_felon`, `ch47_chinook` and `aw159_wildcat`.

- Modern set: nineteen entries, one runtime-ready (`aw101_merlin`). Next source
  class: a US Army OPFOR/ODIN guide or a manufacturer datasheet that states the
  empty weight, the power and, for a rotor, the rotor diameter.
- Historical set: all sixteen entries are leads. Next source class: a US
  military flight manual (TO/TM), an FAA type certificate data sheet, or a
  public-domain DTIC report.

## Fields with no obtainable source

- The fixed-wing `drag_area_m2` is rarely published. It is optional, so the
  kernel default of 0.7 m2 stands. Next source: a NASA NTRS or DTIC
  wind-tunnel report that states the drag coefficient and the wing area.
- The `rated_power_w` of a jet needs a reference speed. The held A-10 and Su-57
  documents state thrust only. Next source: a held manual that states a cruise
  or maximum speed alongside the thrust.
- The `rotor_disc_area_m2` of the AW159 needs a held rotor diameter. Next
  source: the Leonardo AW159 datasheet.
