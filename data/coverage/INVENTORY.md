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

## The last rung

Every measured matcher ends with the type rung, which answers the kind of
item when no identity can: the engine kind for a vehicle or an aircraft,
the caller's family or the config's item type for a device, the kind
screen's verdict for a munition, and the caller's slot for an item. A type
entry names a kind, never a model, and carries no figure, so full
resolution is a graded claim rather than a silent 100%.
