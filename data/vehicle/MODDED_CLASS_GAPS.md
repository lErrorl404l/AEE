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
classes. The catalogue names 434. One stays open. The base game scores 78 of
79.

| Group | Classes | Why the group stays open |
|---|---|---|
| Family label over a generic class | 1 | `rhsusf_fmtv_base` names a family, and every term that would reach it also reaches another class. |

Twelve StaticWeapon emplacements are excluded from the denominator by kind. A
tripod mount, a towed howitzer and a MANPADS post are not vehicles, so they
are neither named nor counted as a gap. The baseline records the exclusion
count.

## The inheritance rung

The matcher's last layer answers a class whose own text names nothing, from
the config parent chain. That closure is a claim about the ENGINE, which the
config declares and anyone can re-check, and not a claim that the mod item is
the real vehicle the ancestor's entry names. Three rules keep it honest:

- the ancestor is matched by classname against the table's mapped classes and
  never by its text, because any mod may rewrite a displayName;
- the nearest mapped ancestor decides, and the matcher does not walk past it;
- the class's own text must name something the ancestor's entry is identified
  by: its catalogue id, an alias or a keyword. A class that names a different
  article is refused, however short the chain.

Seventeen modded classes close on it, and the chain ships with each in
`data/coverage/modded_baseline.json`.

## The evidence for each class closed by ancestry

`chain` is the config parent chain from the class to the ancestor the table
maps. `display` is the config `displayName` the installed content declares.

| Game class | Display | Chain | Entry |
|---|---|---|---|
| `CBRN_Offroad` | Offroad | `Offroad_01_civil_base_F` → `Offroad_01_unarmed_base_F` | `offroad_q7_l200_composite` |
| `LOP_Offroad_base` | Offroad | `Offroad_01_civil_base_F` → `Offroad_01_unarmed_base_F` | `offroad_q7_l200_composite` |
| `LOP_AA_Offroad` | ANA Offroad | `LOP_Offroad_base` → `Offroad_01_civil_base_F` → `Offroad_01_unarmed_base_F` | `offroad_q7_l200_composite` |
| `LOP_AA_Offroad_Police` | ANP Offroad | `LOP_Offroad_base` → `Offroad_01_civil_base_F` → `Offroad_01_unarmed_base_F` | `offroad_q7_l200_composite` |
| `LOP_Offroad_M2_base` | Offroad (M2) | `Offroad_01_armed_base_F` → `Offroad_01_military_base_F` → `Offroad_01_base_F` | `offroad_q7_l200_composite` |
| `LOP_AA_Offroad_M2` | ANA Offroad (M2) | `LOP_Offroad_M2_base` → `Offroad_01_armed_base_F` → `Offroad_01_military_base_F` → `Offroad_01_base_F` | `offroad_q7_l200_composite` |
| `LOP_AA_Offroad_M2_Police` | ANP Offroad (M2) | `LOP_Offroad_M2_base` → `Offroad_01_armed_base_F` → `Offroad_01_military_base_F` → `Offroad_01_base_F` | `offroad_q7_l200_composite` |

The seven are the base game's Offroad body in mod paint. Each class text holds
`offroad`, the entry's own catalogue id holds it, and the chain reaches an
Offroad class the table already maps. The armed variants reach the same body
through `Offroad_01_armed_base_F` and `Offroad_01_military_base_F`, which are
not mapped, and the walk stops at `Offroad_01_base_F`, which is.

Three base game Offroad classes also resolve: `Offroad_01_repair_base_F`,
`Offroad_01_AT_base_F` and `C_Offroad_01_repair_F`. They resolve at the exact
layer, because the Offroad entry maps them, so the rung is not what names
them and they stay in the base half.

## The Zamak family carries the ten KAMAZ retextures

The Project OPFOR KAMAZ trucks descend from the Zamak in config. The wiki
states what the Zamak is, and the statement covers the family, not one body:

> Zamak is simply Kamaz spelt backwards, which is the name of the company
> that designs the real-life "KamAZ-4310" family of trucks that the Zamak is
> based on.

*Zamak*, Trivia, `https://armedassault.fandom.com/wiki/Zamak`.

That citation is the family warrant for binding the Zamak variants to
`kamaz_4310`. It is also the only warrant needed: a retexture of a bound class
is that class in another paint, so the closure repeats a binding the research
already made and adds no claim about a body.

The variants are bound from the game's own declaration. Each carries a
`$STR_A3_` key that the game's stringtable defines, and each is declared under
the game's `Addons` tree, so `tools/validation/gen_vehicle_data.py` keeps the
binding for the runtime table. All 37 records name `kamaz_4310`.

| Game class | Display | Key |
|---|---|---|
| `Truck_02_base_F` | Zamak Transport (Covered) | `$STR_A3_CfgVehicles_Truck_02_Base0` |
| `O_Truck_02_covered_F` | Zamak Transport (Covered) | `$STR_A3_CfgVehicles_Truck_02_Base0` |
| `O_Truck_02_transport_F` | Zamak Transport | `$STR_A3_CfgVehicles_C_Truck_02_Dump0` |
| `O_Truck_02_box_F` | Zamak Repair | `$STR_A3_CfgVehicles_Truck_02_Repair0` |
| `O_Truck_02_fuel_F` | Zamak Fuel | `$STR_A3_CfgVehicles_Truck_02_Fuel0` |
| `O_Truck_02_medical_F` | Zamak Medical | `$STR_A3_CFGVEHICLES_TRUCK_02_MEDICAL` |
| `O_Truck_02_Ammo_F` | Zamak Ammo | `$STR_A3_CFGVEHICLES_TRUCK_02_AMMO` |
| `I_Truck_02_covered_F` | Zamak Transport (Covered) | `$STR_A3_CfgVehicles_Truck_02_Base0` |
| `I_Truck_02_transport_F` | Zamak Transport | `$STR_A3_CfgVehicles_C_Truck_02_Dump0` |
| `I_Truck_02_box_F` | Zamak Repair | `$STR_A3_CfgVehicles_Truck_02_Repair0` |
| `I_Truck_02_fuel_F` | Zamak Fuel | `$STR_A3_CfgVehicles_Truck_02_Fuel0` |
| `I_Truck_02_medical_F` | Zamak Medical | `$STR_A3_CFGVEHICLES_TRUCK_02_MEDICAL` |
| `I_Truck_02_ammo_F` | Zamak Ammo | `$STR_A3_CFGVEHICLES_TRUCK_02_AMMO` |
| `I_Truck_02_MRL_F` | Zamak MRL | `$STR_A3_CfgVehicles_I_Truck_02_MRL_F0` |
| `C_Truck_02_covered_F` | Zamak Transport (Covered) | `$STR_A3_CfgVehicles_Truck_02_Base0` |
| `C_Truck_02_transport_F` | Zamak Transport | `$STR_A3_CfgVehicles_C_Truck_02_Dump0` |
| `C_Truck_02_box_F` | Zamak Repair | `$STR_A3_CfgVehicles_Truck_02_Repair0` |
| `C_Truck_02_fuel_F` | Zamak Fuel | `$STR_A3_CfgVehicles_Truck_02_Fuel0` |
| `C_IDAP_Truck_02_F` | Zamak Transport (Covered) | `$STR_A3_CfgVehicles_Truck_02_Base0` |
| `C_IDAP_Truck_02_transport_F` | Zamak Transport | `$STR_A3_CfgVehicles_C_Truck_02_Dump0` |
| `O_T_Truck_02_F` | Zamak Transport (Covered) | `$STR_A3_CfgVehicles_Truck_02_Base0` |
| `O_T_Truck_02_transport_F` | Zamak Transport | `$STR_A3_CfgVehicles_C_Truck_02_Dump0` |
| `O_T_Truck_02_Box_F` | Zamak Repair | `$STR_A3_CfgVehicles_Truck_02_Repair0` |
| `O_T_Truck_02_fuel_F` | Zamak Fuel | `$STR_A3_CfgVehicles_Truck_02_Fuel0` |
| `O_T_Truck_02_Medical_F` | Zamak Medical | `$STR_A3_CFGVEHICLES_TRUCK_02_MEDICAL` |
| `O_T_Truck_02_Ammo_F` | Zamak Ammo | `$STR_A3_CFGVEHICLES_TRUCK_02_AMMO` |
| `I_E_Truck_02_F` | Zamak Transport (Covered) | `$STR_A3_CfgVehicles_Truck_02_Base0` |
| `I_E_Truck_02_transport_F` | Zamak Transport | `$STR_A3_CfgVehicles_C_Truck_02_Dump0` |
| `I_E_Truck_02_transport_EMP_F` | Zamak Transport | `$STR_A3_CfgVehicles_C_Truck_02_Dump0` |
| `I_E_Truck_02_EMP_F` | Zamak Transport (Covered) | `$STR_A3_CfgVehicles_Truck_02_Base0` |
| `I_E_Truck_02_Box_F` | Zamak Repair | `$STR_A3_CfgVehicles_Truck_02_Repair0` |
| `I_E_Truck_02_fuel_F` | Zamak Fuel | `$STR_A3_CfgVehicles_Truck_02_Fuel0` |
| `I_E_Truck_02_Medical_F` | Zamak Medical | `$STR_A3_CFGVEHICLES_TRUCK_02_MEDICAL` |
| `I_E_Truck_02_Ammo_F` | Zamak Ammo | `$STR_A3_CFGVEHICLES_TRUCK_02_AMMO` |
| `I_E_Truck_02_MRL_F` | Zamak MRL | `$STR_A3_CfgVehicles_I_Truck_02_MRL_F0` |
| `RHS_Civ_Truck_02_covered_F` | Zamak Transport (Covered) | `$STR_A3_CfgVehicles_Truck_02_Base0` |
| `RHS_Civ_Truck_02_transport_F` | Zamak Transport | `$STR_A3_CfgVehicles_C_Truck_02_Dump0` |

The earlier work left the ten open for a reason that the regenerated
artefact removes. It read the display names as unresolved, because the
installed content reopens the Zamak classes with `$STR_ace_realisticnames_*`
keys that no scanned stringtable defines. A class is declared once for the
purposes of the binder: the game's own declaration comes first and it states
the `$STR_A3_` key that `Addons/language_f_gamma` defines. The ACE reopen is a
later declaration, so it never supplied the text.

With the Zamak variants bound, the walk from each retexture stops at the body
it descends from. The class text holds `kamaz`, which the entry is identified
by through its keyword `kamaz`, so the rung answers `kamaz_4310`.

The RHS KamAZ-5350 is unaffected: it does not descend from the Zamak, so no
chain reaches it, and its own keyword still names it. The lock
`test_the_rhs_kamaz_5350_still_resolves_to_the_5350` holds that.

## The two identity-only entries

Two classes name a vehicle that no held document publishes a figure for. Each
has an entry that carries the identity only: `identity_only` is set, `values`
is empty, the entry is not runtime-ready, and its runtime row is labelled
zeros. The identity evidence is the engine class table, the form
`data/vehicle/class_map.json` records as `aee_class_table`, at grade
`claimed`. No document is cited and no source record is added, because the
entry holds no value.

`LOP_Nissan_PKM_base` is `Nissan (PKM)` and inherits `PO_Pickup_PK_base`, a
pickup with a crew-served PKM. The entry `nissan_pickup_technical` names the
maker and no model: Nissan built several pickups, and no held source names the
one in the content, so the D21, Navara and Hardbody designations stay out. The
alias `nissan` names the class, and the ladder answers at the alias layer. The
token `pkm` stays out of the match terms, because 91 scanned classes carry it,
the RHS M1151 vehicles among them, so it would answer an M1151 as a Nissan
technical. The nearest mapped ancestor is the Honda Civic, and it is not the
answer.

`rhsusf_fmtv_base` is `FMTV` and inherits `Truck_01_base_F`. The entry
`fmtv_family` names the United States Army Family of Medium Tactical Vehicles,
claims no M-number and no manufacturer, and holds no figure. It carries no
match term, so the class stays open. The measurement gives the reason. The
token `fmtv` as an alias stops 69 vehicle-table classes and moves four. As a
keyword it ties the four M1078A1R and M1084A1R SOV classes, which resolve on
that layer, and the runtime returns nothing from a layer with more than one
candidate, so those four stop resolving. A class name joined as `fmtvbase` is
not a published designation, so it is not used. The M1078, M1083, M1084 and
M1085 classes resolve to their own entries, and the locks in
`tools/tests/test_mod_class_resolution.py` hold both facts.

The layer rule decides this entry: evidence that ties is not evidence. The
same rule is mirrored in `tools/tests/test_mod_class_resolution.py`, which
counts a tied layer as no answer.

## Aircraft

The modded aircraft gaps are eight ArmaFPV first-person-view drones. No
published source designates a "Crocus" drone. The base game's
`drone_base_F` row ("AR-2 Darter") resolves to the Parrot AR.Drone 2.0 and is
locked closed. The aircraft matcher has no inherited layer, and the rung
would be wrong there: a Crocus FPV drone is not a Parrot AR.Drone, so a chain
from one to the other would mislabel it.

## Armament

The PHAN chemical bombs (`PHEN_FSPLUS_*`) stay open in the vehicle armament
table. They inherit the base game's bomb launcher, and a nerve-agent bomb is
not the high-explosive bomb it inherits from. The rung is a vehicle rung and
does not reach that table, and it would be wrong to extend it there.

## Small arms

The two DSA machine pistols stay open. They name a chambering (`.45`, `9mm`)
and a category (machine-pistol) and no designation. Their ancestors,
`hgun_Pistol_heavy_01_F` and `hgun_P07_F`, are themselves unnamed by the
small-arms corpus, so there is no ancestor entry to inherit even if the
weapon matcher grew the rung.
