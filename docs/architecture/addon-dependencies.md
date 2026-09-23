# Addon dependency map

Generated from the repository, not from memory. Regenerate with
`python3 tools/architecture/addon_dependencies.py`. It scans every
`*.sqf` under `addons/<component>/` for `EFUNC(component,...)` calls and
`EGVAR(component,...)` variable reads, the only two forms a cross-addon
edge can take.

## The map

| addon | depends on |
|---|---|
| `actions` | `core`, `environmental` |
| `armour` | `physiology` |
| `atmos` | `core`, `environmental`, `maritime` |
| `ballistics` | `atmos`, `core` |
| `compat_ace3` | none |
| `compat_acm` | `core`, `environmental` |
| `compat_acre2` | none |
| `compat_kat` | none |
| `compat_realweather` | `core` |
| `compat_tfar` | none |
| `core` | `atmos`, `ballistics`, `environmental`, `fx`, `maritime`, `mobility`, `nightvision`, `optics`, `physiology`, `radio`, `thermal` |
| `environmental` | `compat_acm`, `core`, `material` |
| `fx` | `atmos`, `core`, `optics` |
| `main` | none |
| `maritime` | `core` |
| `material` | none |
| `mobility` | `core`, `environmental`, `material`, `physiology` |
| `nightvision` | `core`, `optics`, `physiology` |
| `optics` | `core`, `nightvision`, `thermal` |
| `physiology` | `core`, `thermal` |
| `radio` | `core`, `environmental`, `physiology` |
| `thermal` | `core`, `environmental`, `material` |

## Reading it

- Leaves (depend on nothing, safe for anything to depend on): `main`, `material`.
- Hubs (depend on most others): `core` (11).
- Compat addons (`compat_*`) load only when their host mod is present. An
  optional read of a compat variable is not an edge in the core set.

## Why this exists

Issue #203 carried a hand-written map whose tiers did not match the
repository, and a cycle between `environmental` and `thermal` went
unnoticed. This file is generated so the two cannot drift apart again.

