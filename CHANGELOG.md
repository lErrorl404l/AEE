# Changelog

All notable changes to this project are documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versioning follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2026-09-11

### Added

- Modular restructure: 18 addons (core, atmos, thermal, ballistics, optics,
  mobility, environmental, maritime, physiology, radio, fx, actions, main,
  and 5 compat addons).
- Canonical ACE3/CBA function wiring in every addon (XEH_PREP, four-link
  XEH chain, functions/fnc_<name>.sqf).
- Component-scoped naming: functions `aee_<component>_fnc_<name>`, state in
  `aee_core_*` mission variables.
- Settings registered with `CBA_fnc_addSetting`, titles in stringtables.
- Standalone core: no ACE3 dependency. Compat addons gate on their host mod
  with `skipWhenMissingDependencies`.
- Deterministic multiplayer state: core atmospheric values are a pure
  function of position, mission time, and engine weather.
- EDEN module (AEE Environment Config).
- Headless dedicated-server test harness (`tools/docker_test.sh`) with a
  five-phase verification mission and baseline-vs-patched comparison.
- Physics reference checks (`tools/tests/test_physics.py`).
- CI: pedantic HEMTT lint gate, SQF validation, SQFVM, stringtable checks,
  SBOM on release tags, release-drafter, dependant bots.
- Licence: GPL-2.0-or-later with a PBO-distribution exception.

### Fixed

- Function compilation: no function was compiled before this release; the
  mod did not run. Wiring now resolves every function (zero undefined).
- ACE3 bridge: removed the fake `ace_weather_current*` variable interface.
  AEE drives engine weather; ACE3 reads engine state.
- Dedicated-server runtime errors found by the headless test: unit params
  default to objNull, bare `call` no longer inherits the caller's `_this`,
  and biome state is written to the core namespace.
- Missing assets: logo references removed from mod.cpp.

[0.1.0]: https://github.com/lErrorl404l/AEE/releases/tag/v0.1.0