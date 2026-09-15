# ACE Environment Extended (AEE)

[![CI](https://github.com/lErrorl404l/AEE/actions/workflows/ci.yml/badge.svg)](https://github.com/lErrorl404l/AEE/actions/workflows/ci.yml)
[![Licence](https://img.shields.io/badge/Licence-GPL--2.0--or--later-blue)](LICENSE)
[![Issues](https://img.shields.io/github/issues/lErrorl404l/AEE)](https://github.com/lErrorl404l/AEE/issues)
[![Project Board](https://img.shields.io/badge/Project_Board-tracker-blue)](https://github.com/orgs/lErrorl404l/projects/2)

Physically accurate environment simulation for Arma 3. Extends ACE3 with models for atmosphere, thermal and optical effects, physiology, mobility, environmental conditions, maritime state, and radio propagation. Each model uses published physics and public standards.

Author: [lErrorl404l](https://github.com/lErrorl404l). Licence: [GPL-2.0-or-later](LICENSE) with a PBO-distribution exception.

---

## Requirements

- Arma 3
- [CBA A3](https://github.com/CBATeam/CBA_A3/releases) (latest version)

The core addons are standalone. ACE3 is optional.

---

## Install

### Workshop (recommended)

1. Subscribe to the mod on Steam Workshop.
2. Launch Arma 3. AEE loads automatically.

### Manual

1. Download the latest release from [Releases](https://github.com/lErrorl404l/AEE/releases).
2. Extract the zip into your Arma 3 `@AEE` folder (or any name you prefer).
3. Launch with `-mod=@CBA_A3;@AEE` in your launch parameters, or enable both in the Arma 3 launcher.

Place the **AEE Environment Config** module in the editor to customise settings.

---

## Features

### Atmosphere

- Elevation lapse rates and diurnal temperature cycles.
- Terrain microclimate, including urban heat islands and water influence.
- True air density from temperature, pressure, and humidity.
- Koppen biome classification with seasonal variation.
- Atmospheric events: lightning (ice-phase gated), sandstorms, dust devils, microbursts (NWS tiers), ICAO eddy-dissipation-rate turbulence, airframe icing.

### Thermal and Optics

- Thermal crossover, mirage, and solar glare.
- Cn2-based atmospheric seeing and physical smoke dispersal.
- Rain visibility (Atlas extinction), dew and frost on optics, snow blindness.

### Physiology

- Wet-bulb globe temperature (ISO 7243 heat-stress categories), NWS heat index, wind chill (JAG/TTI).
- Altitude acclimatisation with time-of-useful-consciousness hypoxia.
- ISO 17166 UV index with ozone absorption, hypothermia and dehydration risk.

### Mobility

- SAE J1349 engine derating by air density, slip-curve traction, mud accretion.
- Nash-cascade river water level, NRMM cone-index route degradation.
- Momentum-theory helicopter lift.

### Environmental

- CBRN persistence (Arrhenius Q10), Rothermel fire spread, avalanche risk.
- Stefan freeze/thaw, flash-flood prediction, surface wetness, scent dispersion.

### Maritime

- Harmonic tidal prediction (M2/S2/K1/O1 constituents).
- WMO Beaufort sea state, Pierson-Moskowitz wave height, magnetic compass deviation.

### Radio

- Friis free-space path loss with atmospheric ducting.
- ITU-R P.531 ionospheric absorption for VHF/UHF/HF.

---

## Compatibility

Six compat addons load only when their host mod is present. Install the ones you need:

| Addon | Host Mod | Purpose |
|-------|----------|---------|
| `compat_ace3` | ACE3 | Maps AEE state onto ACE medical and weather |
| `compat_acre2` | ACRE2 | Custom radio signal-strength callback |
| `compat_tfar` | TFAR | Scales transmission range |
| `compat_kat` | KAT | Drives KAT circulation from AEE dehydration |
| `compat_acm` | ACM | Drives CBRN contamination from AEE persistence |
| `compat_realweather` | Real Weather | Reads `weather.json` and publishes into AEE |

AEE does not drive engine weather directly. It reads engine `overcast`, `rain`, and `wind` as inputs and computes its own state from them. Only `compat_realweather` writes engine overcast, and only on the server.

---

## Multiplayer

Core atmospheric state is deterministic. It is a function of position, mission time, and engine weather. Every machine computes identical values. No `publicVariable` is needed.

Event FX (lightning, dust, sound) vary cosmetically per machine.

---

## Roadmap

AEE develops in three phases. The [project board](https://github.com/orgs/lErrorl404l/projects/2) tracks the 36 issues across them.

1. **Phase 1 Baseline** — Core physics models, unit tests, dedicated-server integration test.
2. **Phase 2 Expansion** — Additional models, more compat addons, expanded test coverage.
3. **Phase 3 Frontier** — Advanced phenomena, edge-case coverage, performance optimisation.

---

## Structure

19 addons under `addons/`.

**Core addons (13):** `main`, `core`, `actions`, `atmos`, `ballistics`, `environmental`, `fx`, `maritime`, `mobility`, `optics`, `physiology`, `radio`, `thermal`.

**Compat addons (6):** `compat_ace3`, `compat_acm`, `compat_acre2`, `compat_kat`, `compat_realweather`, `compat_tfar`.

Build PBO names are `aee_<component>`. For example, the core addon builds to `aee_core.pbo`.

---

## Development

### Naming Conventions

Functions use the name `aee_<component>_fnc_<name>`. For example, `aee_core_fnc_init`.

Shared simulation state lives in `aee_core_*` mission variables. Any mod or mission script can read them.

Each function file is `functions/fnc_<name>.sqf`. The files are registered in `XEH_PREP.hpp` and compiled through CBA XEH (`Extended_PreInit_EventHandlers`). This is the standard ACE3/CBA pattern.

### Settings

AEE registers its settings at mission start with `CBA_fnc_addSetting`. The settings live in `addons/core/initSettings.inc.sqf`, which is included from `XEH_preInit.sqf`. All settings appear under the category "AEE Core" in the CBA settings UI.

### Localisation

Localisation uses a per-addon `stringtable.xml`. Keys use the form `STR_AEE_<Component>_<Key>`.

---

## Build and Test

### Commands

```bash
hemtt check -p -e    # Pedantic lint (warnings are errors)
hemtt build          # Build PBOs
hemtt release        # Sign PBOs, make bikey and zip
hemtt launch <profile>  # Launch game with mod loaded
```

Profiles are `default`, `ace3`, `acre2`, `tfar`, `kat`, `acm`, and `full`. Workshop IDs are configured in `.hemtt/project.toml`.

### Tests

```bash
python3 tools/run_tests.py   # Unit tests and physics validation
```

The unit tests mirror the core physics models in Python. They cover reference values, edge cases, and clamps. A pre-commit hook runs them on every commit.

The headless dedicated-server test in Docker runs the mod against real Arma 3 and verifies ten phases (see `docs/wiki/chapters/testing.qmd`).

---

## CI

GitHub Actions runs on every push:

- `hemtt check -p -e`
- `hemtt build`
- Unit tests via `tools/run_tests.py`
- Headless Docker server test (on demand)
- SBOM on release tags
- Release-drafter

---

## Contributing

The project uses trunk-based development. All commits must be signed.

A pre-commit hook runs:

- `hemtt check -p -e`
- `ste-lint`
- `audit`

Make logical commits. Link each commit to its change rationale. Report vulnerabilities through [SECURITY.md](SECURITY.md).

---

## Links

- [GitHub Repository](https://github.com/lErrorl404l/AEE)
- [Project Board](https://github.com/orgs/lErrorl404l/projects/2)
- [Documentation](https://lerrorl404l.github.io/AEE/)
- [Issues](https://github.com/lErrorl404l/AEE/issues)
