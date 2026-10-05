# Aircraft corpus research gaps

This file lists what the corpus does not yet hold and the next source to try.
It is written by hand and it names a concrete next source for every gap. The
generated reports `SOURCE_GAPS.md` and `CLASS_MAPPING_GAPS.md` carry the same
gaps in table form.

## Dropped or unresolved class mappings

- `I_Plane_Fighter_04_F` (Saab JAS 39C Gripen, Jets DLC) is not present in the
  deployed air config. The base name `I_Plane_Fighter_03_F` is also absent; its
  real variants `I_Plane_Fighter_03_CAS_F`, `I_Plane_Fighter_03_AA_F` and
  `I_Plane_Fighter_03_dynamicLoadout_F` are bound to `l159_alca` instead.
  Next source: verify the Jets DLC class with `hemtt utils config derapify` on
  the `Air_F_Exp` or DLC addon, then bind it to `jas39c_gripen`.
- `O_Heli_Transport_02_F` (Mil Mi-26 Halo analogue) is not present in the
  deployed air config. The CSAT heavy transport classes that do exist are
  `O_Heli_Transport_04_F` and `O_Heli_Transport_04_covered_F`. Next source:
  confirm the Mi-290 Taru class name from the Helicopters DLC config and decide
  whether it maps to `mi26_halo` or needs its own entry.
- `Air` and `UAV` are token-level only. No concrete class binding names a real
  aircraft. Next source: a vanilla `Air` or `UAV` class that carries a real
  analogue.

## Entries that are leads

A lead holds no held runtime value and projects a labelled zero for every
runtime field. The first slice holds seven runtime-ready entries; the rest are
leads.

- First slice leads: `a10a_thunderbolt_ii` (no held reference speed for the
  thrust-to-power derivation), `su25_frogfoot`, `l159_alca` (no held PDF),
  `jas39c_gripen` (no held reference speed), `fa18e_super_hornet` (no held
  thrust), `su57_felon` (no held reference speed), `rah66_comanche` (no held
  power or rotor), `uh60a_black_hawk` (no held power), `ch47_chinook` (no held
  power), `aw159_wildcat` (no held rotor diameter).
  Next source for a jet: a held flight manual that states a reference speed, so
  `rated_power_w = thrust_kn * 1000 * reference_speed_ms` resolves. Next source
  for a rotor: a held manual that states the shaft power.
- Modern set: all nineteen entries are leads. Next source class: a US Army
  OPFOR/ODIN guide or a manufacturer datasheet that states the empty weight,
  the power and, for a rotor, the rotor diameter.
- Historical set: all sixteen entries are leads. Next source class: a US
  military flight manual (TO/TM), an FAA type certificate data sheet, or a
  public-domain DTIC report.

## Fields with no obtainable source

- The fixed-wing `drag_area_m2` is rarely published. It is optional, so the
  kernel default of 0.7 m2 stands. Next source: a NASA NTRS or DTIC
  wind-tunnel report that states the drag coefficient and the wing area.
- The `rated_power_w` of a jet needs a reference speed. The held A-10, Gripen
  and Su-57 documents state thrust only. Next source: a held manual that states
  a cruise or maximum speed alongside the thrust.
- The `rotor_disc_area_m2` of the AW159 needs a held rotor diameter. Next
  source: the Leonardo AW159 datasheet.
