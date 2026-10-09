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
| `ai` | none |
| `armour` | `lib`, `physiology` |
| `atmos` | `core`, `lib`, `weather` |
| `ballistics` | `atmos`, `core`, `lib` |
| `cartography` | `hud`, `lib`, `symbology` |
| `compat_ace3` | none |
| `compat_acm` | `core`, `persistence` |
| `compat_acre2` | none |
| `compat_kat` | none |
| `compat_realweather` | `core` |
| `compat_tfar` | none |
| `core` | `atmos`, `ballistics`, `diagnostics`, `fx`, `lib`, `lighting`, `maritime`, `mobility`, `nightvision`, `optics`, `persistence`, `physiology`, `radio`, `thermal`, `vision`, `weather` |
| `diagnostics` | `core`, `lib` |
| `environmental` | none |
| `eye` | `core`, `lib` |
| `fx` | `atmos`, `ballistics`, `core`, `lib`, `lighting`, `maritime`, `mobility`, `optics` |
| `hud` | `cartography`, `core`, `lib`, `symbology` |
| `lib` | `core` |
| `lighting` | `core`, `lib`, `weather` |
| `maritime` | `core`, `lib` |
| `material` | none |
| `mobility` | `atmos`, `core`, `diagnostics`, `lib`, `material`, `persistence`, `thermal`, `weather` |
| `nightvision` | `core`, `lib`, `thermal` |
| `optics` | `core`, `eye`, `lib`, `nightvision`, `thermal`, `vision` |
| `persistence` | `compat_acm`, `core`, `diagnostics`, `lib`, `material` |
| `physiology` | `core`, `thermal` |
| `radio` | `atmos`, `core`, `diagnostics`, `maritime`, `thermal`, `weather` |
| `symbology` | `cartography`, `lib` |
| `thermal` | `core`, `lib`, `lighting`, `material`, `nightvision`, `optics`, `persistence`, `physiology`, `vision`, `weather` |
| `vision` | `core`, `eye`, `lib`, `lighting`, `nightvision`, `optics`, `thermal` |
| `weather` | `core`, `diagnostics`, `lib`, `persistence`, `physiology` |
| `wildlife` | `ai`, `ballistics`, `core`, `lib`, `material`, `weather` |

## Reading it

- Leaves (depend on nothing, safe for anything to depend on): `ai`, `environmental`, `material`.
- Hubs (depend on most others): `core` (16), `thermal` (10), `fx` (8), `mobility` (8), `vision` (7), `optics` (6), `radio` (6), `wildlife` (6).
- Compat addons (`compat_*`) load only when their host mod is present. An
  optional read of a compat variable is not an edge in the core set.

## Why this exists

Issue #203 carried a hand-written map whose tiers did not match the
repository, and a cycle between `environmental` and `thermal` went
unnoticed. This file is generated so the two cannot drift apart again.

