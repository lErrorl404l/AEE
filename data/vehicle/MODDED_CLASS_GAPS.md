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

The 2026-10-19 scan of the installed content scores 440 modded vehicle
classes. The catalogue names 411. Twenty-nine stay open:

| Group | Classes | Why the group stays open |
|---|---|---|
| StaticWeapon emplacements | 5 | A tripod mount, a towed howitzer and a MANPADS post are not vehicles. A kind rule in `gen_vehicle_bindings.py` excludes them from the denominator. They are not closed here and not counted as a vehicle gap. |
| Fictional display re-use | 12 | The display name is the base game's own fictional name. The text states no real designation. |
| Maker or family name | 12 | The text names a maker or a family and no model. A maker is not a vehicle. |

## The evidence for each open class

`display` is the config `displayName` the installed content declares.
`class text` is the classname. Both are read from the declaring PBO.

| Game class | Display | Declared in | Reason | Evidence |
|---|---|---|---|---|
| `rhs_m2staticmg_base` | M2HB (M3 AA) | rhsusf_c_statics.pbo | StaticWeapon emplacement, excluded by kind | Chain passes `StaticWeapon`; a machine gun mount is not a vehicle |
| `RHS_M2StaticMG_MiniTripod_base` | M2HB (M3) | rhsusf_c_statics.pbo | StaticWeapon emplacement, excluded by kind | Chain passes `StaticWeapon` |
| `RHS_MK19_TriPod_base` | Mk19 (M3) | rhsusf_c_statics.pbo | StaticWeapon emplacement, excluded by kind | Chain passes `StaticWeapon` |
| `RHS_Stinger_AA_pod_Base` | FIM-92F (DMS) | rhsusf_c_statics.pbo | StaticWeapon emplacement, excluded by kind | Chain passes `StaticWeapon` |
| `RHS_M119_base` | M119A2 | rhsusf_c_statics.pbo | StaticWeapon emplacement, excluded by kind | Chain passes `StaticWeapon`; a towed howitzer is not a vehicle |
| `LOP_Offroad_base` | Offroad | po_main.pbo | Fictional Offroad display, contested real identity | `data/vehicle/class_bindings.json` names the Land Rover Wolf; `data/vehicle/stringtable_bindings.json` names the Toyota Land Cruiser J70. Both cannot stand, and choosing one invents an answer |
| `LOP_Offroad_M2_base` | Offroad (M2) | po_main.pbo | Fictional Offroad display, contested real identity | Same two conflicting links; the M2 mount is Arma content, not a real mark |
| `CBRN_Offroad` | Offroad | PHAN_CW.pbo | Fictional Offroad display, contested real identity | Same two conflicting links |
| `LOP_AA_Offroad` | ANA Offroad | po_factions_me.pbo | Fictional Offroad display behind a faction prefix | Class text holds `offroad` and a faction tag only; no real designation |
| `LOP_AA_Offroad_Police` | ANP Offroad | po_factions_me.pbo | Fictional Offroad display behind a faction prefix | Same |
| `LOP_AA_Offroad_M2` | ANA Offroad (M2) | po_factions_me.pbo | Fictional Offroad display behind a faction prefix | Same |
| `LOP_AA_Offroad_M2_Police` | ANP Offroad (M2) | po_factions_me.pbo | Fictional Offroad display behind a faction prefix | Same |
| `LOP_SUV_base` | SUV | po_main.pbo | Fictional SUV display | The text names a body class; SUV is a kind, not a model |
| `LOP_Hatchback_base` | Hatchback | po_main.pbo | Fictional Hatchback display | The text names a body class |
| `CBRN_Containment_Vehicle` | Van (Utility) | PHAN_CW.pbo | Fictional Van display | The text names a body class; no maker and no model |
| `Gendarmerie_CBRN_Vehicle` | Van (Utility) | PHAN_CW.pbo | Fictional Van display | Same |
| `RHS_Civ_Truck_02_transport_F` | Zamak Transport | rhs_c_a2port_car.pbo | Fictional Zamak display | Zamak is the base game's fictional truck; the RHS civilian retexture names no real model |
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

## Why no KamAZ class closes

The corpus now holds the real truck: `data/vehicle/catalogue/kamaz_4310.json`
holds the KamAZ-4310 with its published figures, sourced to
`ru_wikipedia_kamaz_4310`. The entry binds no game class.

The reason is text. The identity ladder reads the classname and the display
name only. The installed Project OPFOR trucks state `KAMAZ` and a body word.
No classname and no display in the whole scan carries `4310`: a search of the
scan for that token returns two Tornado aircraft classes and nothing else.
The mod's own `README.txt` and `mod.cpp` name no vehicle model.

An alias on the maker word would close ten classes and be wrong. The same
alias would capture the RHS KamAZ-5350 classes, which are a different truck,
at the alias layer before their own `kamaz5350` keyword can act. A closure
that renames a 5350 as a 4310 is a defect, not coverage.

The only honest route is a class text that states a model. When a retexture
or a new mod states one, the entry resolves it with no code change.

## Aircraft

The modded aircraft gaps are unchanged. All nine are ArmaFPV first-person-view
drones plus the base game's fictional `AR-2 Darter`. No published source
designates a "Crocus" drone. The lock is in the same test module.
