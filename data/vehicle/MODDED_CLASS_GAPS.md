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
classes. The catalogue names 423. Twelve stay open. The base game scores 78
of 79.

| Group | Classes | Why the group stays open |
|---|---|---|
| Retexture of an ancestor no entry maps | 10 | The Project OPFOR KAMAZ trucks descend from the Zamak in config, and no entry maps the Zamak variants. |
| Maker over another maker's entry | 1 | `LOP_Nissan_PKM_base` names a Nissan over the ancestor's Toyota entry. |
| Family label over a generic class | 1 | `rhsusf_fmtv_base` names a family, and its nearest mapped ancestor is the engine's `Car`. |

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

Seven modded classes close on it, and the chain ships with each in
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

## Why the ten KamAZ retextures stay open

The Project OPFOR trucks descend from the Zamak in config. That is a fact,
and it is not enough, because the rung answers with the identity of the
ancestor the table maps, and no entry maps a Zamak variant.

The earlier work left them open because the ladder read only the classname
and the display name, and the installed trucks state `KAMAZ` and a body word.
No classname and no display in the whole scan carries `4310`. An alias on the
maker word would close ten classes and be wrong, because the same alias would
capture the RHS KamAZ-5350, a different truck, before its own `kamaz5350`
keyword could act.

The chain does not close them either. The Zamak classes (`O_Truck_02_fuel_F`
and its siblings) are named only by their `displayName`, and the installed
content rewrites those with `$STR_ace_realisticnames_*` keys that no string
table in the scanned set defines. The scan holds 1766 rows whose `$STR_ace_*` display name no scanned string
table defines, 605 of them `$STR_ace_realisticnames_*`.
An entry that cannot name the ancestor cannot lend it to a descendant, so the
walk passes the Zamak by, reaches the engine's `Car` class, and the rung
refuses: the class text `KAMAZ` does not name the passenger car that entry
holds.

The alternative is to bind the Zamak variants themselves. That would need a
published identity for each body (fuel, ammo, repair, medical, covered,
transport), and the wiki statement carries only the family: "Zamak is simply
Kamaz spelt backwards, which is the name of the company that designs the
real-life "KamAZ-4310" family of trucks that the Zamak is based on"
(*Zamak*, Trivia, `https://armedassault.fandom.com/wiki/Zamak`). Binding six
bodies to a cargo-truck entry would invent the claim the citation is supposed
to carry, so the work stops short of it.

The RHS KamAZ-5350 is unaffected: it does not descend from the Zamak, so no
chain reaches it, and its own keyword still names it. The lock
`test_the_rhs_kamaz_5350_still_resolves_to_the_5350` holds that.

## The two maker labels

`LOP_Nissan_PKM_base` inherits `PO_Pickup_PK_base`, whose entry is the Toyota
T100. The class text says Nissan. A Nissan is not a Toyota, so the rung
refuses: the ancestor is a different article, not a donor body.

`rhsusf_fmtv_base` inherits `Truck_01_base_F`, which the table does not map.
Its nearest mapped ancestor is the engine's `Car` class, whose entry is a
passenger car. The class text says `FMTV`, which the car's entry does not
carry, so the rung refuses. The entry that would fit is a family of four
M-numbers, and the class text names none of them.

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
