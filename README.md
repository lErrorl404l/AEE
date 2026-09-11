# Advanced Environment Extension (AEE)

AEE is a physically accurate environment simulation for Arma 3. It models
elevation lapse rates, terrain microclimate, true air density, Koppen biome
classification, thermal and physiological effects, optics, mobility,
environmental conditions, maritime state, radio propagation, and atmospheric
events.

The mod is standalone. It requires only CBA_A3. The core addons have no ACE3
dependency.

Author: lErrorl404l. Licence: GPL-2.0-or-later with a PBO-distribution
exception. See LICENSE.

## Features

- Elevation lapse rates and diurnal temperature cycles.
- Terrain microclimate, including urban heat islands and water influence.
- True air density from temperature, pressure, and humidity.
- Koppen biome classification with seasonal variation.
- Thermal and physiological effects, including WBGT and acclimatisation.
- Optics effects, including thermal crossover, mirage, and glare.
- Vehicle and helicopter mobility, including engine derating and lift.
- Environmental effects, including foliage, scent, and fire risk.
- Maritime state, including sea state and tides.
- Radio propagation for VHF, UHF, and HF bands.
- Atmospheric events, including lightning, sandstorms, and microbursts.

## Structure

The project has 18 addons under `addons/`. The 13 core addons are `main`,
`core`, `actions`, `atmos`, `ballistics`, `environmental`, `fx`, `maritime`,
`mobility`, `optics`, `physiology`, `radio`, and `thermal`. The 5 compat
addons are `compat_ace3`, `compat_acm`, `compat_acre2`, `compat_kat`, and
`compat_tfar`.

Build PBO names are `aee_<component>`. For example, the core addon builds to
`aee_core.pbo`.

## Naming Conventions

Functions use the name `aee_<component>_fnc_<name>`. For example,
`aee_core_fnc_init`.

Shared simulation state lives in `aee_core_*` mission variables. Any mod or
mission script can read them.

Each function file is `functions/fnc_<name>.sqf`. The files are registered in
`XEH_PREP.hpp` and compiled through CBA XEH
(`Extended_PreInit_EventHandlers`). This is the standard ACE3/CBA pattern.

## Settings

AEE registers its settings at mission start with `CBA_fnc_addSetting`. The
settings live in `addons/core/initSettings.inc.sqf`, which is included from
`XEH_preInit.sqf`. All settings appear under the category "AEE Core" in the
CBA settings UI.

## Dependencies

The core addons require only CBA_A3. They are standalone.

The five compat addons gate on their host mod. Each uses `requiredAddons` and
`skipWhenMissingDependencies`. A compat addon loads only when its host mod is
present.

`compat_ace3` disables ACE3 weather simulation. AEE drives engine weather
directly with `setWind` and `setFog`.

## Multiplayer

Core atmospheric state is deterministic. It is a function of position,
mission time, and engine weather. Every machine computes identical values.
No `publicVariable` is needed.

Event FX, such as lightning, dust, and sound, vary cosmetically per machine.

The EDEN module, AEE Environment Config, is placed by mission editors. The
module is global.

## Build and Test

Check the project with pedantic mode:

```
hemtt check -p -e
```

Pedantic mode treats warnings as errors. Build the PBOs with:

```
hemtt build
```

Make a release with:

```
hemtt release
```

Release signs the PBOs and makes the bikey and zip files.

Launch the game with:

```
hemtt launch <profile>
```

Profiles are `default`, `ace3`, `acre2`, `tfar`, `kat`, `acm`, and `full`.
Workshop IDs are configured in `.hemtt/project.toml`.

Run the physics reference checks with:

```
python3 -m unittest discover -s tools/tests
```

Localisation uses a per-addon `stringtable.xml`. Keys use the form
`STR_AEE_<Component>_<Key>`.

## Continuous Integration

GitHub Actions runs these checks on every push:

- `hemtt check -p -e`
- `hemtt build`
- The Python validators and physics tests
- An SBOM on release tags
- Release-drafter

## Verification

The recommended in-game test is a headless Linux dedicated server in Docker.
Run missions that write `diag_log` output. Diff the baseline logs against the
patched logs.

This is the primary validation path for mission authors and contributors.

## Contributing

The project uses trunk-based development. All commits must be signed.

A pre-commit hook runs these checks:

- `hemtt check -p -e`
- `ste-lint`
- `audit`

Make logical commits. Link each commit to its change rationale.

Report vulnerabilities through SECURITY.md.