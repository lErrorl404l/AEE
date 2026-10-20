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

## The last rung

Every measured matcher ends with the type rung, which answers the kind of
item when no identity can: the engine kind for a vehicle or an aircraft,
the caller's family or the config's item type for a device, the kind
screen's verdict for a munition, and the caller's slot for an item. A type
entry names a kind, never a model, and carries no figure, so full
resolution is a graded claim rather than a silent 100%.
