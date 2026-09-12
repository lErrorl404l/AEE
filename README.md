# Advanced Environment Extension (AEE)

[![CI](https://github.com/lErrorl404l/AEE/actions/workflows/ci.yml/badge.svg)](https://github.com/lErrorl404l/AEE/actions/workflows/ci.yml)
[![License](https://img.shields.io/badge/license-GPL--2.0--or--later-blue)](LICENSE)

AEE is a physically accurate environment simulation for Arma 3. It models
elevation lapse rates, terrain microclimate, true air density, Koppen biome
classification, thermal and physiological effects, optics, mobility,
environmental conditions, maritime state, radio propagation, and atmospheric
events.

The mod is standalone. It requires only CBA_A3. The core addons have no ACE3
dependency.

Author: [lErrorl404l](https://github.com/lErrorl404l). Licence:
[GPL-2.0-or-later](LICENSE) with a PBO-distribution exception.

## Features

- Elevation lapse rates and diurnal temperature cycles.
- Terrain microclimate, including urban heat islands and water influence.
- True air density from temperature, pressure, and humidity.
- Koppen biome classification with seasonal variation.
- Thermal and physiological effects, including WBGT, NWS heat index,
  altitude acclimatisation with time-of-useful-consciousness hypoxia,
  and ISO 7243 heat-stress categories.
- Optics effects, including thermal crossover, mirage, glare, Cn²-based
  atmospheric seeing, and physical smoke dispersal.
- Vehicle and helicopter mobility, including SAE J1349 engine derating,
  slip-curve traction, and momentum-theory helicopter lift.
- Environmental effects, including foliage, scent, CBRN persistence,
  Rothermel fire spread, avalanche risk, and flash-flood prediction.
- Maritime state, including harmonic tidal prediction (M2/S2/K1/O1) and
  WMO Beaufort sea state.
- Radio propagation from the Friis equation with ITU-R P.531
  ionospheric absorption.
- Atmospheric events, including lightning, sandstorms, and microbursts.

## Structure

The project has 19 addons under `addons/`. The 13 core addons are `main`,
`core`, `actions`, `atmos`, `ballistics`, `environmental`, `fx`, `maritime`,
`mobility`, `optics`, `physiology`, `radio`, and `thermal`. The 6 compat
addons are `compat_ace3`, `compat_acm`, `compat_acre2`, `compat_kat`,
`compat_realweather`, and `compat_tfar`.

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

The six compat addons gate on their host mod. Each uses `requiredAddons` and
`skipWhenMissingDependencies`. A compat addon loads only when its host mod is
present. Each compat layer uses only the host mod's public API, verified
against the host source:

- `compat_ace3` — publishes AEE temperature/humidity/overcast into ACE
  weather state and maps AEE thermal/dehydration state onto ACE medical
  vitals through the public `ace_medical_status_fnc_*` hooks.
- `compat_acm` — drives ACM CBRN contamination from AEE persistence.
- `compat_acre2` — registers an ACRE2 custom signal-strength callback
  driven by AEE radio propagation.
- `compat_kat` — drives KAT circulation body-fluid compartments from AEE
  dehydration.
- `compat_realweather` — reads `weather.json` from the mission folder and
  publishes the real values into AEE state, gating the simulation.
- `compat_tfar` — scales TFAR transmission range from AEE radio
  propagation through the per-unit `tf_sendingDistanceMultiplicator`.

AEE does not drive engine weather directly. It reads engine `overcast`,
`rain`, and `wind` as inputs and computes its own state from them. Only
`compat_realweather` writes engine overcast, and only on the server.

## Multiplayer

Core atmospheric state is deterministic. It is a function of position,
mission time, and engine weather. Every machine computes identical values.
No `publicVariable` is needed.

Event FX, such as lightning, dust, and sound, vary cosmetically per machine.

The EDEN module, AEE Environment Config, is placed by mission editors. The
module is global.

## Build and Test

Check the project with pedantic mode:

```bash
hemtt check -p -e
```

Pedantic mode treats warnings as errors. Build the PBOs with:

```bash
hemtt build
```

Make a release with:

```bash
hemtt release
```

Release signs the PBOs and makes the bikey and zip files.

Launch the game with:

```bash
hemtt launch <profile>
```

Profiles are `default`, `ace3`, `acre2`, `tfar`, `kat`, `acm`, and `full`.
Workshop IDs are configured in `.hemtt/project.toml`.

Run the full test sweep (unit suites + physics validation harness) with:

```bash
python3 tools/run_tests.py
```

The 170 unit tests mirror every physics model in Python and cover
reference values, edge cases, and clamps. A pre-commit hook runs them on
every commit. The headless dedicated-server test in Docker runs the mod
against real Arma 3 and verifies ten phases (see docs/wiki/chapters/testing.qmd).

Localisation uses a per-addon `stringtable.xml`. Keys use the form
`STR_AEE_<Component>_<Key>`.

## Continuous Integration

GitHub Actions runs these checks on every push:

- `hemtt check -p -e`
- `hemtt build`
- The unit tests via `tools/run_tests.py`
- The headless Docker server test (on demand)
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

Report vulnerabilities through [SECURITY.md](SECURITY.md).