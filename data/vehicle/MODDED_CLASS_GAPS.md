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
classes. The catalogue names 434, which is 99.8 %. One class stays open. The
base game scores 77 of 79.

| Group | Classes | Why the group stays open |
|---|---|---|
| A configuration word on a family stem | 1 | `rhsusf_RG33_base` names `RG33 4X4 SOCOM`. `rg334x4` is a keyword of both RG-33 4x4 entries, so the keyword layer matches two rows and refuses the tie, and the family rung is never reached. The M-number that would answer, M1238, is not in the class text. |

Twelve StaticWeapon emplacements are excluded from the denominator by kind. A
tripod mount, a towed howitzer and a MANPADS post are not vehicles, so they
are neither named nor counted as a gap. The baseline records the exclusion
count.

## The family rung of 2026-10-20

A class that names a family and no mark had no rung to answer it. The family
now has one, at confidence 7, last of all: a family entry is identity-only,
names the family and no mark, publishes the family designation as its keyword,
and is generated into its own `_families` table that no higher rung reads.
The rung answers only when exactly one family row matches, and a tie is
still a refusal, so a class that ties at a higher layer stays open.

Five family entries carry the corpus: `t72_family`, `rg33_family`,
`landrover_family`, `fmtv_family` and no T-90 entry. The T-90 family is not
captured: `t90` is already a curated alias of the T-90 mark, and a family
entry owning the same word would break the rule that a family designation is
never a mark's alias. The T-90SA classes close without one, on `t90sa`,
because no mark holds the stem `t90s` now.

A designation a family entry owns is dropped from every mark row. That is the
same reserved-name rule the generator already applies to a base model, and it
is what lets the family rung answer at all: while the T-72B mark carried the
derived keyword `t72`, every query naming the family tied there.

| Classes | Entry that answers | Layer |
|---|---|---|
| `LOP_LandRover_base_02`, `LOP_LandRover_mg_base` | `landrover_family` | family |
| `rhssaf_army_t72s` | `t_72ms` | keyword, after `t72` left the T-72B mark |
| `rhsusf_fmtv_base` | `fmtv_family` | family |
| `rhsusf_RG33_CROWS_base`, `rhsusf_RG33_CROWSMK19_base` | `bae_systems_rg_33_4x4_socom_m1238` | keyword, on `m1238`, after `rg33` left the mark rows |
| `rhsusf_rg33_d`, `rhsusf_rg33_m2_d` | `rg33_family` | family |

Eight classes closed and none stopped resolving. The check compared
`(class, display) -> entry` for all 1,344 scored classes before and after, so
the 17 inherited closures and `kamaz_5350_mustang` are unchanged with it.

One class moved. `LOP_T72_base` displays `T-72` and answered the T-72M4CZ,
because the M4CZ carried `t72` as a curated alias, which is the shape the rule
forbids. With the alias gone the classname's own glue answered instead:
`LOP_T72_base` folds to `lopt72base`, which holds `t72b`, the T-72B mark's
published designation, so the keyword layer named `t_72b_obr_1984g`. That was
a weaker answer for a class that displays `T-72`. The derived-stem rule below
drops `t72b` from the T-72B mark, so the family rung now answers with
`t72_family`, which is the right identity for a class that names only T-72.
The class is a Project OPFOR scaffolding base that no unit places. The move is
recorded here so the next change has the evidence.

## The derived-stem rule of 2026-10-20

A mark must not hold a word that another mark's designation extends. The
keyword layer matches by substring, so a short stem answers every query that a
longer designation answers. The T-72B obr. 1984g. mark derives `t72b` from
"T-72B", and `t72b` is a substring of "T-72B3", so the mark tied with the
T-72B3 mark and the runtime refused the query.
`tools/validation/gen_vehicle_data.py` now drops a derived keyword when
another entry's key extends it, and keeps a key that only its own entry
extends.

Four classes closed on their own text, and none stopped resolving:

| Game class | Display | Term that closed it |
|---|---|---|
| `rhs_t72bd_tv` | T-72B3 (obr. 2012g.) | `t72b3`, after `t72b` left the T-72B obr. 1984g. mark |
| `rhs_t72be_tv` | T-72B3 (obr. 2016g.) | `t72b3` in its own text |
| `rhs_t90saa_tv` | T-90SA (obr. 2004g.) | `t90sa`, after the `t-90s` alias left the T-90 mark |
| `rhs_t90sab_tv` | T-90SA (obr. 2016g.) | `t90sa` in its own text |

The T-90 closure has two halves. The T-90 mark curated `t-90s`, a partial
designation that the T-90SA and the T-90SM both extend, so the alias layer
could not answer and the query fell to a tie. That alias is gone. The derived
`t90s`, which both T-90 marks carry from their own canonical names, leaves by
the same rule. Each mark then answers on its own `t90sa` or `t90sm`.

The rule adds no data. Both marks were already in the corpus with their own
sources: `t_72b3_obr_2012g` cites `ru_wikipedia_d0_a2_72_d0_913` and
`wikipedia_t_72`, and `t_90sa` cites `wikipedia_t_90`.

The check compared `(class, display) -> entry` for all 514 scored classes
before and after. The four closures and the `LOP_T72_base` move are the only
changes.

## The one class that stays open

| Game class | Display | Why it stays open |
|---|---|---|
| `rhsusf_RG33_base` | RG33 4X4 SOCOM | The text names the family and a configuration. `rg334x4` is a keyword of both RG-33 4x4 entries, so the keyword layer matches two rows and refuses the tie, and the family rung is never reached. The M-number that would answer, M1238, is not in the class text. A class whose text names it closes on it: `rhsusf_RG33_CROWS_base` and `rhsusf_RG33_CROWSMK19_base`. |

## The family-word work of 2026-10-20

A family or maker word must not be an alias or a keyword of one specific
mark. A word that names a family reaches every member, so the layer ties and
the runtime answers nothing. Thirty classes closed when the family word left
the specific mark it was blocking:

| Classes | Entry that answers | Term removed | From |
|---|---|---|---|
| 12 M113A3 (`rhsusf_m113_usarmy*`, `LOP_M113_base`, `LOP_AA_M113_*`) | `m113a3` | `m113` | the alias set of `m113a2` |
| 16 M1240A1 (`rhsusf_m1240a1_*`) | `m_atv_m1240a1` | `m1240` | the alias set of `m_atv_m1240` |
| 1 M977A4 (`rhsusf_HEMTT_A4_base`) | `m977a4` | `hemtt` | the alias set of `m977_hemtt`, where it stays a keyword |
| 1 BTR-70 (`rhs_btr_base`) | `btr_70` | `btr` | the keyword set of `btr_70` and `btr_80` |

The M1240 case is the one to read closely. The mod displays "M1240" on a
class whose classname carries `m1240a1`, so the text names both marks. The
family designation left the base entry, which still answers `matv` and
`hunter`, and the A1 classes close on `m1240a1` at the alias layer. Removing
the term from the A1 entry instead would have moved the tie to the keyword
layer, where the derived `m1240` keyword is still a substring of `m1240a1`.

The HEMTT family keeps `hemtt` as a keyword, because fourteen base and modded
HEMTT classes are named by that word alone. The alias layer reaches `m977a4`
first for the A4 class, and the keyword layer names the family for the other
fourteen.

No class changed entry, and no class stopped resolving, in any of the four
batches. The check compared `(class, display) -> entry` for all 514 scored
classes before and after each batch.

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

## The identity-only and family entries

Six entries name a vehicle and publish no figure: the Nissan pickup, and the
five family entries. Each has an entry that carries the identity only:
`identity_only` is set, `values` is empty, the entry is not runtime-ready, and
its runtime row is labelled zeros. The identity evidence is the engine class
table, the form `data/vehicle/class_map.json` records as `aee_class_table`, at
grade `claimed`. No document is cited and no source record is added, because
the entry holds no value.

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
claims no M-number and no manufacturer, and holds no figure. It is a family
entry: it publishes the family designation `fmtv` as its keyword and is read
by the family rung alone, from its own table, so the four M1078A1R and
M1084A1R SOV classes keep resolving on the mark table and the base class
itself now answers the family. The M1078, M1083, M1084 and M1085 classes
resolve to their own entries.

The layer rule decides every entry: evidence that ties is not evidence. A
family entry avoids the tie by living in a table that no mark layer reads, not
by weakening the rule. The same rule is mirrored in
`tools/tests/test_mod_class_resolution.py`, which counts a tied layer as no
answer.

## Aircraft

The modded aircraft gaps have their own record,
`data/aircraft/MODDED_CLASS_GAPS.md`. Forty-two stay open: ten F/A-181
loadout configurations of an Arma 3 fictional type, eight ArmaFPV Crocus
drones that no published source designates, and twenty-four that tie at a
layer above the family rung. The base game's `drone_base_F` row ("AR-2
Darter") resolves to the Parrot AR.Drone 2.0 and is locked closed.

## Armament

The vehicle armament gaps are the gap list
`data/coverage/modded_gaps_vehicle_armament.txt` and the lock
`data/munition/modded_coverage.json`. Thirty-six stay open. The PHAN chemical
bombs (`PHEN_FSPLUS_*`) are one group: a nerve-agent bomb is not the
high-explosive store it inherits from, so no HE entry may answer it. The rest
name a role or a description ("1000 lb HE bombs", "WP Marker Rockets", "Smoke
Launcher"), a mark the corpus does not hold, or a designation the catalogue
carries on two entries at once.

## Small arms

The two DSA machine pistols stay open. They name a chambering (`.45`, `9mm`)
and a category (machine-pistol) and no designation. Their ancestors,
`hgun_Pistol_heavy_01_F` and `hgun_P07_F`, are themselves unnamed by the
small-arms corpus, so there is no ancestor entry to inherit even if the
weapon matcher grew the rung.
