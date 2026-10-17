# Addon dependency map

Generated from the repository, not from memory. Regenerate with
`python3 tools/architecture/addon_dependencies.py`. It scans every
`*.sqf` under `addons/<component>/` for `EFUNC(component,...)` calls and
`EGVAR(component,...)` variable reads, the only two forms a cross-addon
edge can take.

## The map

| addon | depends on |
|---|---|
| `actions` | `core`, `maritime`, `nightvision`, `persistence` |
| `ai` | `core`, `lib`, `mobility`, `persistence`, `physiology`, `vision`, `weather` |
| `altitude` | `core`, `dive`, `lib`, `physiology`, `strain` |
| `ambience` | `lib`, `wildlife` |
| `armour` | `ballistics`, `clothing`, `lib` |
| `atmos` | `core`, `lib`, `weather` |
| `ballistics` | `atmos`, `core`, `lib` |
| `blast` | `clothing`, `lib` |
| `cartography` | `atmos`, `core`, `hud`, `lib`, `material`, `radio`, `symbology`, `weather` |
| `clothing` | `physiology`, `thermal` |
| `compat_ace3` | none |
| `compat_acm` | `core`, `persistence` |
| `compat_acre2` | none |
| `compat_kat` | none |
| `compat_tfar` | none |
| `core` | `altitude`, `atmos`, `ballistics`, `clothing`, `diagnostics`, `flight`, `hydrology`, `lib`, `lighting`, `magnetism`, `maritime`, `mobility`, `nightvision`, `optics`, `particles`, `persistence`, `physiology`, `radio`, `strain`, `thermal`, `vehicles`, `vision`, `weather`, `weatherfx` |
| `diagnostics` | `core`, `lib` |
| `dive` | `lib`, `physiology` |
| `eye` | `core`, `lib`, `vision` |
| `flight` | `atmos`, `core`, `lib` |
| `hud` | `cartography`, `core`, `lib`, `radio`, `symbology`, `weather` |
| `hydrology` | `core`, `lib`, `material`, `weather` |
| `lib` | `core` |
| `lighting` | `core`, `lib`, `weather` |
| `ltm` | `lib` |
| `magnetism` | `core`, `lib` |
| `maritime` | `core`, `lib`, `magnetism` |
| `material` | none |
| `mobility` | `core`, `material`, `persistence`, `vehicles` |
| `nightvision` | `core`, `lib`, `ltm`, `thermal` |
| `optics` | `atmos`, `core`, `eye`, `lib`, `nightvision`, `thermal`, `vision` |
| `particles` | `atmos`, `ballistics`, `blast`, `core`, `lib`, `maritime`, `weatherfx` |
| `persistence` | `atmos`, `compat_acm`, `core`, `diagnostics`, `lib`, `material` |
| `physiology` | `altitude`, `core`, `dive`, `strain` |
| `radio` | `atmos`, `core`, `diagnostics`, `lib`, `maritime`, `thermal`, `weather` |
| `strain` | `clothing`, `core`, `lib`, `physiology` |
| `symbology` | `cartography`, `lib` |
| `thermal` | `altitude`, `atmos`, `clothing`, `core`, `lib`, `lighting`, `material`, `nightvision`, `optics`, `persistence`, `thermal_display`, `vision`, `weather` |
| `thermal_display` | `core`, `lib`, `nightvision`, `thermal` |
| `vehicles` | `core`, `diagnostics`, `lib`, `material`, `thermal` |
| `vision` | `core`, `eye`, `lib`, `lighting`, `nightvision`, `optics`, `thermal`, `thermal_display` |
| `weather` | `atmos`, `core`, `diagnostics`, `lib`, `persistence` |
| `weatherfx` | `atmos`, `ballistics`, `core`, `flight`, `hydrology`, `lib`, `lighting`, `mobility`, `optics`, `particles`, `vehicles` |
| `wildlife` | `ai`, `ambience`, `ballistics`, `core`, `lib`, `material`, `weather` |

## Reading it

- Leaves (depend on nothing, safe for anything to depend on): `material`.
- Hubs (depend on most others): `core` (24), `thermal` (13), `weatherfx` (11), `cartography` (8), `vision` (8), `ai` (7), `optics` (7), `particles` (7), `radio` (7), `wildlife` (7), `hud` (6), `persistence` (6).
- Compat addons (`compat_*`) load only when their host mod is present. An
  optional read of a compat variable is not an edge in the core set.

## Why this exists

Issue #203 carried a hand-written map whose tiers did not match the
repository, and a cycle between `environmental` and `thermal` went
unnoticed. This file is generated so the two cannot drift apart again.

