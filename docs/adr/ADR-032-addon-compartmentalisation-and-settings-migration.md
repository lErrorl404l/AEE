# ADR-032: Addon compartmentalisation and settings migration

Status: Accepted
Date: 2026-10-09
Decision: Split the 24 addons into 45, one cohesive module per addon, with a
new `lib` infrastructure addon. Rename every setting to
`aee_<module>_<leaf>` and MIGRATE each stored `profileNamespace` value once,
rather than register an alias. Keep the config-root ceiling: each config
class has exactly one declaring PBO.

## Context

`optics` is 115 functions and 11 config fragments. `environmental` is 72
functions. `thermal`, `mobility`, `physiology` and `wildlife` mix a physical
model with a display surface, a data lookup or an acoustic layer. One addon
owns many settings that a user cannot toggle apart, and one addon declares
several unrelated config roots.

The split is mechanical but the edit surface is large: 45 addons, 21 new
folders, 13 generators, 82 path-citing test files and 12 docker probes. The
migration must not change a physics value, a default or a feature gate. The
plan is `.omo/plans/aee-addon-compartmentalisation.md`.

Settings are stored in `profileNamespace` under their exact name (ADR-012).
CBA 3.19.0 has no alias facility: `addons/lib/script_macros.hpp` records
that CBA has no `addSettingSimple` and no macro parent. A rename therefore
loses a stored value unless the value is copied.

## Decision

1. **The target tree is 45 addons.** `optics` becomes six (`optics`,
   `symbology`, `cartography`, `hud`, `eye`, `vision`); `environmental`
   becomes three (`weather`, `lighting`, `persistence`); `physiology` five;
   `mobility` four; `core` two plus `lib`; `fx`, `thermal`, `wildlife`,
   `nightvision` and `maritime` two each; the twelve single-purpose addons
   (`actions`, `ai`, `armour`, `atmos`, `ballistics`, the six `compat_*`,
   `material`, `radio`) stay. `main` retires into `lib`. The map is
   `docs/architecture/addon-map.json`.

2. **The `lib` boundary.** `lib` owns the framework only:
   `script_mod.hpp`, `script_version.hpp`, `script_debug.hpp`,
   `script_macros.hpp` (`FUNC`/`EFUNC`/`PREP`/`PREPS`, the `AEE_SETTING_*`
   macros, the logging macros, the module-init guards, the path helpers),
   the shared control base classes, the keybind helper, the settings
   migration helper, and the pure shared kernels: the geo set (14),
   `createPPEffect`, `destroyPPEffect`, `deterministicRandom`, `readState`,
   `getWorldLocation`, and the three engine-handler installers. `lib` owns
   **no setting value**: the `AEE_SETTING_*` macros are definitions, and
   every module keeps its own `initSettings.inc.sqf` and its own keys. This
   is what lets one module be toggled on its own. `lib` also holds no
   runtime state beyond the PP registry (`aee_core_ppRegistry`).

3. **Settings MIGRATE, do not alias.** Each setting is renamed to
   `aee_<module>_<leaf>`, where `<module>` is the destination addon folder
   name and the leaf is kept verbatim. The leaf is kept verbatim so the map
   is bijective and collision-free: a stripped leaf would map both
   `hudEnabled` and `trackerEnabled` to `aee_hud_enabled`. The complete map
   is `docs/architecture/settings-map.json`. `lib` provides
   `fnc_migrateLegacySettings.sqf`; it takes `[oldName, newName]` pairs and
   a version tag, and on first run copies each set old value to the new
   name, then sets `aee_settings_migrated_v<version>`. It is idempotent.
   Each module calls it in `XEH_preInit.sqf` before its
   `initSettings.inc.sqf` include, so `CBA_fnc_addSetting` reads the
   migrated value. The pairs live in
   `addons/<module>/data/settingsMigration.sqf`.

4. **The alias alternative is rejected.** An alias means registering the old
   name a second time as a hidden knob, because CBA has no rename. That
   doubles the registry and leaves a permanent legacy surface, and it breaks
   the "one module owns its settings" rule. Migration copies the value once
   and then the old name is gone.

5. **The config-root ceiling holds.** Each config class has exactly one
   declaring PBO. A config root may be reopened only by its owning PBO to
   declare distinct classes. The owner assignment: `CfgFontFamilies`,
   `CfgLocationTypes`, `RscMapControl` to `cartography`; `CfgMarkers`,
   `CfgMarkerClasses`, `CfgMarkerColors` to `symbology`; `CfgWorlds` to
   `lighting`; `CfgClothing` to `clothing`; `CfgCloudlets` to `particles`
   (consolidated: the `core` sand/snow cloudlets move here); `RscTitles`
   splits by display owner (`hud`, `vision`, `cartography`); the shared
   control bases and the PP registry to `lib`.

6. **The ceilings and risks** are recorded in section 6 of the plan and
   summarised here: CBA named presets cannot be migrated; `lib` is the new
   single point of failure; `core` is the hub and cannot be split further;
   the PP registry is shared state; `ColorAEE` and the affiliation classes
   are a runtime contract and stay in `symbology`; a live parallel worker
   edits the same config files; generated files fail `--check` the moment a
   path moves; `requiredVersion = 2.04` in `optics` is an outlier; the
   environmental/thermal cycle must not return; the docker texture-path
   probes are string literals; two copies of `z\aee\` cannot load together.

## Plan-versus-tree corrections

The map was enumerated from the tree. These counts differ from the plan
prose; the tree wins.

- `physiology`: the plan implies 39 functions; the tree has 40 (the root
  `fnc_dumpState.sqf` is not in section 2e). It stays in `physiology`.
- `fx`: the plan implies 31 functions; the tree has 32 (the root
  `fnc_dumpState.sqf` is not in section 2h). It goes to `particles`.
- `thermal`: section 2f lists 25 `display/` object functions; the tree has
  26. The tree also has three root functions not in the plan
  (`calculateBatteryTemperatureDerating`, `handleImpactHeat`, `dumpState`);
  all three stay in `thermal`.
- `atmos`: section 2a says 23 functions; the tree has 24 (plus
  `fnc_dumpState.sqf`).
- `maritime`: section 2i lists 6 moving functions; the tree has 7 (plus
  `fnc_dumpState.sqf`, which stays in `maritime`).
- `optics` settings: section 3 says `aee_optics_eye*` is 12; the tree has
  13.
- `core` settings: section 3 says 34; the tree has 38 (two are the
  `GNSS`/`mgrs` literals `aee_core_mgrsTables` and the mirrored
  `aee_core_logDebug`). The consistency and diagnostic switches still move
  to `diagnostics`.
- `environmental`: section 3 gives no per-name list. The map assigns each
  setting from its consumer. Two settings are read across the new boundary:
  `aee_physiology_ScentIntensity` is consumed by the scent-dispersion
  function (now `weather`) and moves to `weather`; `slabDensity` is read by
  both `calculateSnowAccumulation` (`weather`) and `calculateAvalancheRisk`
  (`persistence`) and stays in `persistence`.
- `physiology` settings with no in-addon reader (`fatigueEnabled`,
  `stabilityEnabled`, `seatReclined`, `gsuitEquipped`) were assigned by
  model ownership: `fatigueEnabled`/`stabilityEnabled` to `strain`,
  `seatReclined`/`gsuitEquipped` to `altitude`.
- `thermal` settings: section 3's `thermal_display` list names 15 leaves.
  Eight display-facing settings not named there (`thermalPalette`,
  `thermalDisplayMode`, `thermalBaseChannel`, `thermalManualMinC`,
  `thermalManualMaxC`, `thermalPolarity`, `activeIR`,
  `thermalTemporalNoise`) stay `aee_thermal_*` pending a follow-up, so the
  map matches section 3 exactly.

## Consequences

- Good: one addon is one module. A user can toggle a module on its own. A
  stored setting value survives the rename. Every move is driven by one
  map, so a step is reversible and idempotent.
- Cost: 21 new addon folders, 45 `CfgPatches`, and a one-time migration
  block per split addon. The rewrite tool and the generators are re-pointed
  once.
- Risk: a missed rename drops a value. `test_settings_migration.py` and the
  completeness check over `docs/architecture/settings-map.json` are the
  guards. A missed cross-addon `EFUNC` breaks load order; the extended
  `test_addon_dependencies.py` cycle guard is the guard.

## References

- Plan: `.omo/plans/aee-addon-compartmentalisation.md` (sections 1 to 6).
- `docs/architecture/addon-map.json`: the file, symbol and config-root map.
- `docs/architecture/settings-map.json`: every old setting name to its new
  name.
- `docs/architecture/addon-dependencies.md`: the one-way edge map.
- ADR-012: CBA settings taxonomy and the `profileNamespace` storage fact.
- ADR-027: ownership architecture, the config-root ceiling and declared
  sovereignty.
- `addons/lib/script_macros.hpp`: the `AEE_SETTING_*` definitions and the
  CBA no-alias note.
