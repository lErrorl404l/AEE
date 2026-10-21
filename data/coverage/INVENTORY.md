# Generated identity tables: inventory and measured scope

Every generator that writes an SQF identity table or matcher, the file it
writes, the corpus it reads, the runtime function that runs the ladder, and
the game class the table is scored against. The measurement lives in
`tools/report_match_coverage.py`; the numbers are in `modded_baseline.json`
and the worklists in `modded_gaps_<table>.txt`.

## Measured

| Generator | SQF output | Corpus | Runtime matcher | Class kind | Table slug |
|---|---|---|---|---|---|
| `tools/validation/gen_vehicle_data.py` | `addons/vehicles/functions/fnc_getVehicleMatch.sqf` | `data/vehicle/` | `aee_vehicles_fnc_getVehicleMatch` | `CfgVehicles`, ground, `LandVehicle` and not `StaticWeapon` | `vehicles` |
| `tools/validation/gen_aircraft_data.py` | `addons/flight/functions/fnc_getAircraftMatch.sqf` | `data/aircraft/` | `aee_flight_fnc_getAircraftMatch` | `CfgVehicles`, chain passes `Air`, `Helicopter`, `Plane` or `UAV` | `aircraft` |
| `tools/validation/gen_runtime_weapons.py` | `addons/ballistics/functions/fnc_getWeaponData.sqf` | `data/ballistics/weapons.json` | `aee_ballistics_fnc_getWeaponData` | `CfgWeapons`, feeding firearm under `RifleCore` or `PistolCore` | `small_arms` |
| `tools/validation/gen_runtime_weapons.py` | the same table | the same corpus | the same matcher | `CfgWeapons`, chain passes `Launcher_Base_F`: a launcher a soldier carries | `carried_launchers` |
| `tools/validation/gen_munition_data.py` | `addons/blast/functions/munition/fnc_getMunitionMatch.sqf` | `data/munition/` | `aee_blast_fnc_getMunitionMatch` | `CfgWeapons`, armament root, filtered by `tools/validation/munition_kind.py` | `vehicle_armament` |
| `tools/validation/gen_device_data.py` | `addons/nightvision/functions/fnc_getDeviceMatch.sqf` | `data/device/` | `aee_nightvision_fnc_getDeviceMatch` | `CfgWeapons`, chain passes `NVGoggles` (family `nvg`) | `night_vision_devices` |
| `tools/validation/gen_equipment_data.py` | `addons/clothing/functions/clothing/fnc_getItemMass.sqf` | `data/equipment/sources/*.json` | `aee_clothing_fnc_getItemMass` | `CfgWeapons`, chain passes `Uniform_Base` | `uniforms` |
| the same | the same | the same | the same | `CfgWeapons`, chain passes `Vest_Camo_Base` or `Vest_NoCamo_Base` | `vests` |
| the same | the same | the same | the same | `CfgWeapons`, chain passes `HelmetBase` | `helmets` |
| the same | the same | the same | the same | `CfgVehicles`, chain passes `Bag_Base` | `rucksacks` |

## Generated, and not measured here

| Generator | SQF output | Corpus | Matcher | Why it is not scored |
|---|---|---|---|---|
| `tools/validation/gen_runtime_cartridges.py` | `addons/ballistics/functions/fnc_getCartridgeData.sqf` | `data/ballistics/` | `aee_ballistics_fnc_getCartridgeData` | It scores a `CfgAmmo` classname, and the scan can supply one through the `CfgMagazines >> ammo` join. The ladder does not end at the alias table: an unmatched class falls to the calibre band through `aee_ballistics_fnc_parseCaliber` and `selectBand`. A mirror of the alias rows alone would understate coverage, so the table is named here and not scored until the band rung is mirrored. |
| `tools/validation/gen_runtime_projectiles.py` | `addons/ballistics/functions/fnc_getProjectileData.sqf` | `data/ballistics/` | `aee_ballistics_fnc_getProjectileData` | Same kind and same reason. |
| `tools/validation/gen_runtime_loads.py` | `addons/ballistics/functions/fnc_getLoadData.sqf` | `data/ballistics/loads.json` | `aee_ballistics_fnc_getLoadData` | Same kind and same reason. |
| `tools/gen_weapon_mass_fallback.py` | `addons/clothing/functions/clothing/fnc_weaponMassFallback.sqf` | `data/ballistics/weapons.json` | reached only after `aee_clothing_fnc_getWeaponMass` | It is the fallback of the weapon-mass lookup, not an identity table: it scores a family keyword and holds no per-class entry. |
| `tools/validation/gen_aircraft_systems.py` | `addons/flight/functions/fnc_getAircraftSystems.sqf` | `data/aircraft/` | thin consumer of `aee_flight_fnc_getAircraftMatch` | No ladder of its own, so its coverage is the aircraft table's coverage. |
| `tools/validation/gen_vehicle_mass_model.py` | `addons/vehicles/functions/fnc_getVehicleMassModel.sqf` | `data/vehicle/mass_model.json` | bands keyed on live config properties | Keyed on extent and mass, not on identity text. |
| `tools/validation/gen_thermal_optics.py` | `addons/thermal/generated/ThermalOptics.hpp` | `data/device/` | none: per-class config patch from `class_bindings.json` | A config writer, not an SQF matcher. |
| `tools/validation/gen_engine_overrides.py`, `gen_physics_config.py` | `CfgMagazines.hpp`, `CfgAmmo.hpp`, `CfgVehicles.hpp` | `data/` | none | Config writers. |
| `tools/gen_fuel_data.py`, `gen_daylight.py`, `gen_gnss.py`, `gen_tide_constituents.py`, `gen_twilight.py`, `gen_wmm.py`, `gen_space_weather.py`, `gen_ownership_sentinels.py` | hashmap and numeric tables | `data/physics/`, `data/` | none | Keyed on a physical quantity, not on a game class. |
| `tools/validation/gen_mgrs_tables.py`, `gen_symbology_tables.py`, `gen_terrain_tables.py`, `gen_meteor_showers.py`, `gen_wildlife_ecology.py`, `tools/gen_variation_families.py` | `mgrs_tables.sqf`, `symbology_tables.sqf`, `terrain_symbols.sqf`, `fnc_meteorShowers.sqf`, `ecology_corpus.sqf`, `asset_map.sqf`, `variation_families.sqf` | `data/` | lookup kernels | Keyed on a grid, a symbol, a Koppen code or a terrain, not on a config class. |

## The device and item tables are bounded by the config

`tools/scan_game_classes.py` records `CfgWeapons >> ItemInfo`: the slot
item class, the numeric item type, the optics modes, and whether a mode
declares a thermal palette or the thermal vision mode. With that, the
device table's families are each bounded on the installed content:

- `night_vision_devices` (family `nvg`): every `CfgWeapons` class whose
  chain passes `NVGoggles`.
- `thermal_optics`: every class declaring optics modes with a thermal
  palette or the thermal vision mode.
- `optics`: every class declaring optics modes.

`fnc_getItemMass.sqf` holds suppressor, medical, tool, radio and other slot
categories that are not scored here: the campaign measures the four worn
or carried slots the operator named. The ladder itself is shared, so a
category added to the measured set needs one table row and no new mirror.

## Classes that leave a clothing table

Each exclusion is counted by the kind it is, in the baseline `excluded`
field, and listed by name in `data/coverage/excluded_classes.txt` (3,900
entries, written by the report so a number is never the only record).

| Table | Bucket | Classes | Why |
|---|---|---|---|
| uniforms | abstract base classes | 4 | scaffolding (`Uniform_Base`, `JCA_U_Base_F`) |
| uniforms | civilian garment | 4,586 | civilian clothing in the uniform slot |
| uniforms | fictional garment | 134 | Arma-invented outfits (guerrilla, alien) with no real product |
| uniforms | no identity text | 210 | classes with no display name at all |

All three uniform buckets run only on classes already at the type grade,
so no resolved garment is touched. The 1,168 uniforms still at type are
real uniforms (M88, M93, Gorka, G3, Flora, VKPO, 6Sh122, M10, pilot
coveralls) whose makers publish no garment mass.
| uniforms | misdeclared headwear | 3,696 | headwear declared in the uniform slot; every class is `NAVSPECWARGRU2_TACDEV_Baseball_*` or `NAVSPECWARGRU2_..._Cap_*` |
| vests | abstract base classes | 9 | `Vest_Camo_Base`, `Vest_NoCamo_Base` and mod bases |
| vests | non-wearable overlays | 7 | `guts`, `bulletholes`, `damagedchest`, `backgore` |
| helmets | abstract base classes | 8 | `HelmetBase` and mod bases |
| rucksacks | abstract base classes | 14 | `Bag_Base`, `Weapon_Bag_Base`, radio bases |
| rucksacks | weapon bags | 74 | dismantled HMG/GMG, static launchers |
| rucksacks | weapon support bags | 29 | folded tripods, bipods, mortar tubes, gun bags |
| rucksacks | parachutes | 15 | `B_Parachute_*` |
| rucksacks | radio bags | 45 | TFAR bags, `RT-1523G`, radio bags |

After the exclusions the four tables hold 16,967 uniforms, 544 vests, 216
helmets and 642 rucksacks. The four rucksack classes still at type are the
three vanilla Outdoor Packs, which have no published mass, and
`CFP_Cutters`, a bolt cutter carried in a bag slot rather than a rucksack.

## Sourced optics added for the type set

Seven products are now corpus entries with captured manufacturer
documents. The held file, its sha256 and its locator are in
`data/device/sources.json`, and the bytes are in `data/device/sources/`.

| Entry | Figures held | Document (tier 4) | Classes moved onto it |
|---|---|---|---|
| `nightforce_nxs_3515x50` | 15x top power, 50 mm, 0.850 kg, exit pupil 3.3 mm derived | Nightforce product page, sha256 `4c16cd5d…` | 4 |
| `nightforce_nxs_5522x56` | 22x top power, 56 mm, 0.907 kg, exit pupil 2.5 mm derived | Nightforce product page, sha256 `d8b2a4df…` | 4 |
| `leupold_mark8_cqbss` | 1.1-8x, 24 mm, 0.666 kg, 17.4 deg at 1.1x, exit pupil 3.0 mm derived | Leupold product page, sha256 `a6cfc3a2…` | 5 |
| `sig_tango6t` | 1-6x, 24 mm, 0.626 kg FFP and 0.590 kg SFP (both named), exit pupil 4.0 mm derived; no FoV or eye relief published | SIG TANGO6T page, sha256 `b54da900…` | 5 |
| `vortex_razor_hd_gen2` | 1-6x, 24 mm, 0.610 kg, 21.7 deg at 1x, exit pupil 4.0 mm derived | Vortex product page, sha256 `38261bfe…` | none: see below |
| `elcan_specter_dr` | 1x/4x, 32 mm entrance pupil, 0.640 kg, 24 deg at 1x, 7.8 mm exit pupil | Raytheon ELCAN datasheet (crawler mirror), sha256 `26818fd7…` | 1 |
| `upo1_1p29` | 4x, 8 deg, 35 mm eye relief, 6.5 mm exit pupil, 0.800 kg; 1P29 is the military designation of the UPO-1 / UPO-1-1 civil variants | NPZ UPO-1 page and manual, sha256 `034ec99e…` and `d432b520…` | 6 |

Three products stay at type, with the reason recorded:

- **Vortex Razor HD Gen II 1-6x24**: no class names it. The mod's Razor
  classes are the Gen III 1-10x, a different product, and the derived
  keyword `genii` is a substring of "GEN III", so the entry's canonical
  name states the family and range only and no class binds to it.
- **Trijicon AccuPower 1-8x28**: the line is retired. Both the product
  path and the discontinued path return 404, and the 2021 archived family
  and detail pages hold no specification table. No figure entered.
- **OKP-7**: no manufacturer site and no datasheet exist; every result is
  a forum post, a wiki or a reseller. No figure entered.
- **PGO-7V**: the only reachable manufacturer page is the Belarusian
  licensee's **PGO-7V3**, a different variant (2.7x, 0.62 kg, 13 deg). Its
  figures are held at sha256 `0bb3bfbb…` but are deliberately not entered
  against the PGO-7V classes, which stay type until a 7V datasheet is held.

The Mark 8 entry corrects an earlier note in this file. That note said the
Leupold specification table is client-side rendered and unavailable. It is
not: the held bytes (355,785 bytes, sha256 `a6cfc3a2…`) contain the whole
specifications block server-rendered, and the figures above are read from
it. The earlier statement was wrong.

## Classes that leave the night vision table

`CfgWeapons >> NVGoggles` is the engine's night-vision slot, and mods hang
more than night vision on it. Each group leaves the table under the kind it
is, and every class is listed in `data/coverage/excluded_classes.txt`:

| Bucket | Classes | Why |
|---|---|---|
| NVG mounts | 79 | Wilcox L4 G24 / L4 G19 / L4 GPNVG and Rhino mounts: the shoe the device clips to, not a device |
| non-NVG item in the NVG slot | 26 | M40 gas masks (20), KAT armbands (4), KAT eye covers (2) |
| engine-integrated goggles | 3 | `Integrated_NVG_*`: engine internals with no product |
| fictional in-game device | 2 | "Spook vision" and "Zombie Eyes" |

The table holds 217 devices after the exclusions and 5 remain at type: the
DSA retextures, `CUP_NVG_HMNVS`, `EF_LPNVG`, the two RHS 6M2 variants and
`rhsusf_ihadss_scope`, for which no reachable manufacturer datasheet states
the figures the NVG row needs. Data coverage is 97.7 percent.

## Thermal optics

The three classes at type are Arma 3's own `optic_tws`, `optic_tws_mg` and
`optic_Nightstalker`: fictional in-game sights with no manufacturer
product. They are real items of this table, so they are not bucketed; they
stay type because no published figure exists for them, and the nearest real
sight (AN/PAS-13) is a different product.

## Vehicle armament: what is sourced and what has no product

The 386 scored classes sit on sourced entries for 366 (94.8 percent). Three
groups make up the rest:

| Group | Classes | State |
|---|---|---|
| Arma in-game armament (Titan, Skyfire, Zephyr, Falchion, Macer, Shrieker, Sahr, Sharur, Tratnyr, DAR, LOM-250G, railgun, the cannon families, GMG, HMG, RCWS) | 26 | bucketed as "Arma in-game armament, no product": real items of the table that no source can name; listed in `excluded_classes.txt` |
| Bound to an existing sourced entry by class name | 17 | GBU-12, GBU-16, CBU-104, CBU-105, Mk 82 SnakeEye, CRV7 (3), APKWS (3), AZP-23 (2), Kh-25 MTP/MS/MPU, GAU-12 |
| Still type | 20 | GBU-55 and GBU-56 (LJDAM 1000/2000 lb: no catalogue entry, and a nominal weight is not a mass, so no figure is borrowed from GBU-31/32); the mod-only names M301, 902A, BA-21, FURY, Mikholit, SAMPT21, GP19, FULGER, Smokewinder, CHF/FLR, the PHAN gas bombs and the ANZ WP rockets, which name no product a source documents |

## Aircraft: the measured outcome of the class bindings

The 266 scored classes sit on sourced entries for 250 (94.0 percent). The
figure was 221 (83.1 percent). The gain is 29 class bindings in
`data/aircraft/class_bindings.json`. No figure and no catalogue entry was
added. Each binding names the entry the class text already claims.

| Group | Classes | Entry |
|---|---|---|
| F/A-181 Black Wasp napalm and GBU loadout fits | 10 | `fa18e_super_hornet`, the entry the family class `B_Plane_Fighter_01_F` already binds |
| UH-80 and MH-80 Ghost Hawk variants | 3 | `uh60a_black_hawk` |
| AH-64D marks: `fza_ah64d_b1`, `fza_ah64d_b2e` and the five RHS AH-64D classes | 7 | `ah64d_apache_longbow` |
| Gunships held by a shared role word | 4 | `mi24p_hind_f` (Mi-24P), `su25sm_frogfoot` (Su-25, 2), `uh1h_iroquois` (UH-1H) |
| The SOAR MH-60M, the vtx UH-60M base and the HH-60G Pavehawk | 3 | `mh60m`, `uh60m_black_hawk`, `hh60g_pave_hawk` |
| The AW101 Merlin class and the F/A-18F ECM decoy | 2 | `aw101_merlin`, `fa18f_super_hornet` |

Every binding records the token that held the ladder at a tie: `a18` read
inside `fa181`, `ah64` beside `ah6`, `cas`, `heavy`, `gunship`, `su25`,
`mh60`, `blackhawk`, `pavehawk`, `ghost`, `hawk`, `merlin` and `hornet`.

Sixteen aircraft classes stay at type, one reason each:

- **ArmaFPV Crocus drones, 8**: `ARMAFPV_Crocus_AT_Base`,
  `ARMAFPV_Crocus_AP_Base` and the six `O_/B_/I_Crocus_*_TI` variants.
  ArmaFPV is a fictional system and no published designation exists. The six
  sidecar classes `O_/B_/I_Crocus_*` carry no display name, so they never
  enter the table.
- **RHS Mi-8MTV-3, 6**: `rhs_mi8mtv3_base`, `rhs_mi8mtv3_heavy_base`,
  `RHS_Mi8MTV3_vvs`, `RHS_Mi8mtv3_Cargo_vvs`, `RHS_Mi8MTV3_FAB_vvs` and
  `RHS_Mi8MTV3_UPK23_vvs`. The catalogue holds no Mi-8MTV-3 entry, so the
  keyword `mi8` ties the Mi-8T, the Mi-17 and the Mi-8AMTSh. Those are
  different marks, so no binding is written.
- **`RHS_AH64_base`**: its display prints `AH-64` and names no mark, and the
  catalogue holds the AH-64A, the AH-64D and the AH-64E.
- **`FIR_ECM_Dummy_1`**: an ECM decoy whose display prints `F-16C`, where the
  shared alias `falcon` also answers the F-16A entry and the catalogue holds
  two F-16C blocks. The display names no single entry.

## Optics: second sourcing pass

Fourteen products are now corpus entries with held manufacturer documents
under `data/device/sources/`, each with its digest and locator in
`data/device/sources.json`:

| Entry | Figures held | Classes bound |
|---|---|---|
| `aimpoint_micro_t1` | 1x, 18 mm clear aperture, 84 g | 8 |
| `aimpoint_micro_t2` | 1x, 18 mm; **mass absent** — the page states 102 g in its table and 94 g on its card, so neither is entered | 15 |
| `eotech_xps3` | 1x, 255 g | 8 (the G33 + XPS3 combos) |
| `eotech_g33` | 3x, 300 g with mount, exit pupil 7.6 mm | none: every class naming it also names a sight |
| `eotech_vudu_1_6x24` | 1-6x, 24 mm, 570 g | 6, at family level (the class text fixes no magnification) |
| `trijicon_ta01nsn` | 4x, 32 mm, 7 deg, 442.25 g, exit pupil 8.13 mm | 8 |
| `trijicon_ta31rco` | 4x, 32 mm, 7 deg, 422.41 g, exit pupil 8.13 mm | 33 |
| `trijicon_ta11mgo` | 3.5x, 35 mm, 5.5 deg, 498.95 g, exit pupil 9.91 mm | 1 |
| `trijicon_mro` | 1x, 25 mm, 136.08 g | none: no class names it |
| `trijicon_rm05` | 1x, 34.02 g | 3 |
| `trijicon_reap35` | 1.75x, 35 mm, 12 deg, 798.89 g | 1 (class says "20"; only the 35 mm page exists) |
| `vortex_razor_gen3` | 1-10x, 24 mm, 609.5 g | 7 |
| `sb_pmii_3_12x50` | 3-12x, 50 mm, 860 g, exit pupil 4.3 mm | 1 |
| `sb_pmii_5_25x56` | 5-25x, 56 mm, 1125 g, exit pupil 2.3 mm | 3 |

Bucketed after matching, class lists in `excluded_classes.txt`:
**Arma in-game optic** 44 (ARCO, ACO, Holosight, SOS, MRCO, LRPS, DMS, MRD,
Yorris, Nightstalker, TWS, AMS, KHS, the ACE 2D/PIP re-renders, R3F
J4/J8/J10/NF/NF42/FELIN) and **identity failure** 4 (`R3F_ZEISS`,
`rhsusf_acc_mrds`, the two `DH 5-20x56` declarations).

Left at type, grouped: Nightforce ATACR and NXS (Cloudflare Turnstile,
archives 429 — the NXS entry already in the corpus binds 8 classes, the
ATACR classes do not name a magnification), Trijicon AccuPower 5 (retired,
no spec table), Leupold Mark 4 / M8541 / premier 6 (line withdrawn, archives
429), ELCAN M145 MGO 2 (parking page), AN/PVS-27 and XM157 (no maker page),
BelOMO PK-AS and NIT-A 5 (host times out), NPZ 1P63 / 1PN34 / PGO-7V 6 (not
in the catalogue), NPZ 1P76 Rakurs 1 (the only page is the civilian
PO1x20-A, so it is not bound to the military class), SMAW and MAAWS sights
13, MG42 AA sight 1, L2A2 SUIT 3, AN/PVS-2 1, M2A1 GL sight 1, R3F Zeiss
and the RH_ family (no identity text or no page), and `Scot_LEU_MK8_T2`
whose Mark 8 variant is not caught by the entry and is under investigation.

## Optics: variants of the sourced products

Every variant of a sourced optic is bound to its own product: Mark 8 CQBSS
5 classes (base, RMR, RMR Top, RMR Top Canted, T1), SIG TANGO6T 5 (same
five), 1P29/UPO-1 6 (base, PKP, AS Val and their 3D variants), ELCAN
Specter DR 1 (`rhsusf_acc_elcan_3d`), Nightforce NXS 8. No variant of a
sourced product is left at type.

The 20 type classes that carry a variant suffix belong to products the
corpus does not hold, so the suffix cannot bind:

| Group | Classes | Reason |
|---|---|---|
| Trijicon AccuPower RMR/T1 | 5 | retired line, no specification table in any archive |
| Vortex Razor Gen III RMR/T1 | 5 | the mod holds the Gen III 1-10x; the corpus entry is the Gen II 1-6x24, a different product |
| `ACE_optic_*_2D`, `_PIP` | 7 | 2D and PIP re-renders of Arma's own fictional optics |
| `rhs_acc_nita_3d`, `rhsgref_acc_l2a2_3d`, `rhsusf_acc_elcan_pip` | 3 | 3D or PIP variants of optics that are themselves at type (NIT-A, L2A2 SUIT, M145 MGO) |

The remaining ~105 optics type classes are Arma's fictional sights (ARCO,
ACO, Holosight, MRCO, SOS, DMS, LRPS, MRD, Yorris, Nightstalker, TWS) and
real mod optics with no capture: Trijicon Reap-IR, EOTech Vudu, Nightforce
ATACR, Leupold Mk 4 / M8541 / premier, AN/PVS-27, AN/PAS-13, M145 MGO,
PK-AS, 1P63, OKP-7, NIT-A, PGO-7V, 1PN34, DH 5-20x56, 1P76, T1/RM05/MRDS,
G33/XPS3, SMAW and MAAWS sights, MG42 AA sight, L2A2 SUIT, AN/PVS-2, Zeiss
and Schmidt & Bender entries from R3F, XM157 prototype.

## The last rung

Every measured matcher ends with the type rung, which answers the kind of
item when no identity can: the engine kind for a vehicle or an aircraft,
the caller's family or the config's item type for a device, the kind
screen's verdict for a munition, and the caller's slot for an item. A type
entry names a kind, never a model, and carries no figure, so full
resolution is a graded claim rather than a silent 100%.
