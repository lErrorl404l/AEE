# Modded class gaps: the classes that stay unnamed

This record lists every modded vehicle class that the identity ladder cannot
name, with the reason it stays open and the evidence for that reason. The
coverage measurement reads the list. The lock that fails when a class moves
is `tools/tests/test_mod_class_resolution.py`.

## How the split is measured

A class is base game when the PBO that declares it sits in the game's own
`Addons` directory (196 PBOs). Every other declaring PBO is modded. The
inheritance chain is read from the full scan, so a modded class keeps a base
game parent, and only a class declared by a modded PBO is scored.

The 2026-10-20 scan of the installed content scores 435 modded vehicle
classes. The catalogue names 416. Nineteen stay open, in two groups:

| Group | Classes | Why the group stays open |
|---|---|---|
| Fictional display re-use | 7 | The display name is the base game's own fictional name and the class text names no donor. |
| Maker or family name | 12 | The text names a maker or a family and no model. A maker is not a vehicle. |

Five StaticWeapon emplacements are excluded from the denominator by kind. A
tripod mount, a towed howitzer and a MANPADS post are not vehicles, so they
are neither named nor counted as a gap. They are listed below under
`excluded`, and the baseline records the exclusion count.

## The evidence for each open class

`display` is the config `displayName` the installed content declares.
`class text` is the classname. Both are read from the declaring PBO.

| Game class | Display | Declared in | Reason | Evidence |
|---|---|---|---|---|
| `LOP_Offroad_base` | Offroad | po_main.pbo | Fictional Offroad display | The real identity is a two-donor composite (Audi Q7 pickup-concept front, Mitsubishi L200 rear); the text names neither donor |
| `LOP_Offroad_M2_base` | Offroad (M2) | po_main.pbo | Fictional Offroad display | The same composite identity; the M2 mount is Arma content, not a real mark |
| `CBRN_Offroad` | Offroad | PHAN_CW.pbo | Fictional Offroad display | The same composite identity as the base game |
| `LOP_AA_Offroad` | ANA Offroad | po_factions_me.pbo | Fictional Offroad display behind a faction prefix | The text holds `offroad` and a faction tag only; no donor is named |
| `LOP_AA_Offroad_Police` | ANP Offroad | po_factions_me.pbo | Fictional Offroad display behind a faction prefix | Same |
| `LOP_AA_Offroad_M2` | ANA Offroad (M2) | po_factions_me.pbo | Fictional Offroad display behind a faction prefix | Same |
| `LOP_AA_Offroad_M2_Police` | ANP Offroad (M2) | po_factions_me.pbo | Fictional Offroad display behind a faction prefix | Same |
| `LOP_KAMAZ_fuel_base` | KamAZ (fuel) | po_main.pbo | Maker plus a body word, no model | Class text folds to `lopkamazfuelbase`; the only designation token is `kamaz`, a maker |
| `LOP_UKR_KAMAZ_Fuel` | KAMAZ (fuel) | po_factions_eu.pbo | Maker plus a body word, no model | Same; no digit token |
| `LOP_CDF_KAMAZ_Fuel` | KAMAZ (fuel) | po_factions_fic.pbo | Maker plus a body word, no model | Same |
| `LOP_IRAN_KAMAZ_Fuel` | KAMAZ (fuel) | po_factions_me.pbo | Maker plus a body word, no model | Same |
| `LOP_SYR_KAMAZ_Fuel` | KAMAZ (fuel) | po_factions_me.pbo | Maker plus a body word, no model | Same |
| `LOP_KAMAZ_cov_base` | KAMAZ (covered) | po_main.pbo | Maker plus a body word, no model | Same; the class name states a body, not a mark |
| `LOP_KAMAZ_trans_base` | KAMAZ (open) | po_main.pbo | Maker plus a body word, no model | Same |
| `LOP_KAMAZ_rep_base` | KAMAZ (repair) | po_main.pbo | Maker plus a body word, no model | Same |
| `LOP_KAMAZ_med_base` | Kamaz Medical | po_main.pbo | Maker plus a body word, no model | Same |
| `LOP_KAMAZ_ammo_base` | KAMAZ (ammo) | po_main.pbo | Maker plus a body word, no model | Same |
| `rhsusf_fmtv_base` | FMTV | rhsusf_c_fmtv.pbo | Family label, no M-number | The class name carries `fmtv` and no designation. The four corpus entries (M1078, M1083, M1084, M1085) cannot be told apart from it |
| `LOP_Nissan_PKM_base` | Nissan (PKM) | po_main.pbo | Maker plus the fitted weapon | The text holds `nissan` and `pkm`. PKM is a machine gun, not a vehicle mark |

## Why no KamAZ retexture closes

The corpus holds the real truck: `data/vehicle/catalogue/kamaz_4310.json`
holds the KamAZ-4310 with its published figures, sourced to
`ru_wikipedia_kamaz_4310`. The Arma 3 Zamak classes are bound to it,
`I_Truck_02_transport_F` and `O_Truck_02_transport_F` among them, through the
wiki's own relation: "Zamak is simply Kamaz spelt backwards, which is the
name of the company that designs the real-life "KamAZ-4310" family of trucks
that the Zamak is based on" (*Zamak*, Trivia,
`https://armedassault.fandom.com/wiki/Zamak`).

The ten Project OPFOR KAMAZ classes stay open for two reasons.

The first is text. The identity ladder reads the classname and the display
name only. The installed Project OPFOR trucks state `KAMAZ` and a body word.
No classname and no display in the whole scan carries `4310`: a search of the
scan for that token returns two Tornado aircraft classes and nothing else.
The mod's own `README.txt` and `mod.cpp` name no vehicle model.

The second is chain. The retextures look like retextures of the Zamak, and the
parent chain passes `O_Truck_02_*`, but no source read for the counterpart
research states that the mod's KAMAZ is the base game's Zamak with new paint.
A parent class is inheritance in config, not a published identity, so binding
through it would invent the claim the citation is supposed to carry.

An alias on the maker word would close ten classes and be wrong. The same
alias would capture the RHS KamAZ-5350 classes, which are a different truck,
at the alias layer before their own `kamaz5350` keyword can act. A closure
that renames a 5350 as a 4310 is a defect, not coverage.

The only honest route is a class text that states a model, or a published
source that states the retexture chain. When either arrives, the entry
resolves it with no code change.

## Aircraft

The modded aircraft gaps are eight ArmaFPV first-person-view drones. No
published source designates a "Crocus" drone. The base game's
`drone_base_F` row ("AR-2 Darter") now resolves to the Parrot AR.Drone 2.0
and is locked closed. The lock is in the same test module.
