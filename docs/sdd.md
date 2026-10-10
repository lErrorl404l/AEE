# Software Design Description

This description states how AEE is built. It is the design baseline for the
software CIs named in `docs/cmp.md` section 2.

The design traces to the requirements in `docs/srs.md`. Every design choice
that a later change must respect has an ADR under `docs/adr/`.

## 1. Design overview

AEE is a set of Arma 3 addons. One addon is one Configuration Item. The
engine loads the addons in the order the dependency graph allows.

The design has three rules.

1. One producer per variable. The producer addon owns the variable. A
   consumer reads it across the boundary. No two addons write one variable.
2. One direction per boundary. The producer must initialise before the
   consumer reads. The boundaries are in `docs/icd/`.
3. Generate from a cited corpus. A value table is generated from a data
   file that names its source. A hand-typed table is not allowed.

ADR-027 records the ownership model. ADR-034 records the framework. ADR-032
records the addon split.

## 2. Addon decomposition

The addon tree has 45 addons. The tree is in
`docs/architecture/addon-map.json`. The dependency graph is generated from
the source by `tools/architecture/addon_dependencies.py`, and written to
`docs/architecture/addon-dependencies.md`.

The graph has two shapes.

- A leaf addon depends on nothing. `ai` and `material` are leaves. Anything
  may depend on a leaf.
- A hub addon depends on most others. `core` is the main hub. `thermal`,
  `weatherfx`, and `vision` are hubs.

The tree is cyclic through `core`. ADR-032 and the guard
`tools/tests/test_addon_dependencies.py` pin the cycles. A new cycle fails
the guard.

`material` holds a shared soil property so that `weather` and `thermal` do
not depend on each other. Issue #203 records the defect the leaf closed.

## 3. Interface design

The boundary between two addons is a variable contract. A producer writes a
variable as `EGVAR(<producer>,<leaf>)`. A consumer reads it as
`EGVAR(<producer>,<leaf>)` or `QEGVAR(<producer>,<leaf>)`. Those are the
only two cross-addon read forms.

The contracts are in `docs/icd/`. Each contract names the producer, the
consumer, the variables, and the direction. The generator
`tools/architecture/interface_contracts.py` derives them from the source.
The gate `tools/tests/test_icd_docs.py` proves every named variable is a
real cross-addon read.

A cross-addon call must be declared in the consumer `CfgPatches`
`requiredAddons[]`. The guard `test_addon_dependencies.py` checks the
declaration.

## 4. Simulation design

The engine keeps the solver, the renderer, and the physics step (ADR-017,
ADR-034). The mod observes the published state and calls published
functions. The mod does not run a second engine.

The orchestrator is the `core` addon. Its function `updateEnvironment`
runs the per-tick update. A producer computes its state in that update. A
consumer reads the published state.

The native kernels compute the heavy work. A kernel runs in the native dev
extension. Each kernel has an SQF fallback (ADR-036). A parity test pins
the two forms to one result.

## 5. Configuration design

A setting is registered through CBA. The taxonomy is in ADR-012. The
generator `tools/validation/gen_config_docs.py` reads every declared
setting and writes `docs/wiki/chapters/configuration.qmd`. The gate
`tools/tests/test_config_docs.py` proves the chapter is fresh and complete.

A vehicle or aircraft value comes from a data corpus under `data/`. The
corpus names its source. The generator `tools/validation/gen_physics_config.py`
owns the one `CfgVehicles` block. A build-time predicate governs each
emitted key.

The engine reference in `docs/engine/` states what a config may override.
A config change reads the engine source first (ADR-001). A value the engine
cannot reach is recorded as a ceiling.

## 6. Settings and compatibility

A compatibility addon is named `compat_<host>`. It loads only when the host
mod is present. The compat addons are `compat_ace3`, `compat_acm`,
`compat_acre2`, `compat_kat`, `compat_realweather`, and `compat_tfar`.

The engine version floor is set in `addons/lib/script_mod.hpp`. Every addon
reads that floor. The floor is the highest engine command version AEE uses.

## 7. Observability design

The dev console reports the published state and the gate results. The
design rule is evidence over assertion (ADR-035). A console value names the
producer of the value.

The nightly headless regression (ADR-011) runs the soak suite. ADR-015
records the soak observability.

## 8. Design constraints

- A change reads the engine source before it changes a config (ADR-001).
- A change that alters a settled choice adds an ADR.
- A new cross-addon read adds an interface contract and a `requiredAddons[]`
  entry.
- A new value table is generated from a cited corpus.
- A new native kernel adds a parity test.

## 9. Related records

- `docs/architecture/addon-dependencies.md` - the generated addon graph.
- `docs/architecture/vehicle-systems-pipeline.md` - the shared vehicle
  pipeline.
- `docs/icd/README.md` - the interface contract index.
- `docs/engine/README.md` - the engine reference rule.
- `docs/adr/ADR-027-ownership-architecture.md` - the ownership model.
- `docs/adr/ADR-032-addon-compartmentalisation-and-settings-migration.md` -
  the addon split.
- `docs/adr/ADR-034-framework-architecture.md` - the framework.
