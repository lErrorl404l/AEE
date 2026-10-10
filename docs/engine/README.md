# Engine reference

Durable, source-backed reference for the Arma 3 engine. A worker reads this
before any configuration change. It records what the engine does, what a mod
can override, and what it cannot. Every engine claim carries a source and a
line.

## The rule

Before ANY config change:

1. Read the engine's own config for the class. Do not guess the parent.
2. Restate the real parent in the reopen. A bare reopen strips the parent and
   every inherited value.
3. Override only our keys. Name no field we do not own.
4. Forward-declare an external parent at the nested scope, never at the file
   root.
5. Generate from a cited corpus.
6. Pin the value with a test.
7. Declare the dependency in `requiredAddons[]`.
8. Record the ceiling when the engine cannot be reached.

The full eight-step pattern, the config roots with their engine source and
line, and the override mechanisms are in
[engine-config-surface.md](engine-config-surface.md).

## Dev tooling rule

Before a change to a dev tool that touches the engine, read this reference
first. The dev console, the dev harness and the native kernels read engine
state and call engine commands, so they obey the same rule as a config
change: read the engine first, then change.

A dev tool holds no engine state. It observes the published state and calls
published functions. The engine keeps the solver, the renderer and the
physics step (ADR-017, ADR-034). A dev tool that needs a new engine anchor
adds a ceiling here first.

## Index

| Document | Covers |
|---|---|
| [engine-config-surface.md](engine-config-surface.md) | The global config roots, each with its engine source and line, the override mechanisms, and the eight-step pattern. |
| [engine-override-surface.md](engine-override-surface.md) | A class-by-class verdict: ADOPT, ALREADY, RECONCILE, REJECT. |
| [engine-commands-and-features.md](engine-commands-and-features.md) | The SQF commands by job, the engine systems behind them, and the consolidated ceiling list. |
| [engine-command-inventory.md](engine-command-inventory.md) | The complete engine command inventory: every command group, its command count and its Arma 3 version, from the local command DB. The capstone of the #141-#147 series. |
| [dev-tooling.md](dev-tooling.md) | The dev console, the workbench and the native kernels against the engine: the read-first rule and the dev ceilings. |
| [engine-pbo-inventory.md](engine-pbo-inventory.md) | Every engine PBO, its root, what it carries, and the raw header layout. Machine form in `engine-pbo-inventory.json`. |
| [arma-map-grid-semantics.md](arma-map-grid-semantics.md) | The map grid colour and geometry fields, resolved from the open-sourced engine source. |
| [topo-map-surface.md](topo-map-surface.md) | The rendered-map fields a mod controls, and the map fields the engine keeps. |
| [topo-standards.md](topo-standards.md) | Published topographic colour values and contour intervals. |
| [map-baseline.md](map-baseline.md) | The vanilla Arma map baseline, field by field, and the AEE delta per field. |
| [workshop-mod-licence-survey.md](workshop-mod-licence-survey.md) | Per-mod licence facts for the surveyed Workshop mods. |
| [aee-adopt-plan.md](aee-adopt-plan.md) | The per-mod adopt decision that follows the survey. |
| [engine-power-unit-resolution.md](engine-power-unit-resolution.md) | The `enginePower` unit verdict: a PhysX tuning value, with the probe evidence. |

The machine companion is `engine-pbo-inventory.json`.

## How to reproduce a source

The documents name a PBO and a line, never a path on one machine. To read the
same source:

```
hemtt utils pbo unpack <pbo> <outdir>
hemtt utils config derapify <outdir>/config.bin
```

`derapify` writes `config.cpp` beside `config.bin`. The engine ignores a
`config.bin` when a `config.cpp` sits in the same PBO.

## Related records

- `docs/adr/ADR-001-engine-anchors.md` - the three override mechanisms.
- `docs/adr/ADR-017-flight-physics-ceiling.md` - the engine-internal simulation.
- `docs/adr/ADR-027-ownership-architecture.md` - ownership by declaration.
- `docs/adr/ADR-031-conformance-layer-self-describing-detect-and-repair.md` -
  the conformance layer.
- `docs/adr/ADR-037-physx-mass-surface-and-the-grade-gate.md` - the PhysX mass
  surface, the build-time grade gate and the closed surfaces.
- `docs/wiki/research/engine-override-surface.md` - the published copy of the
  engine override surface study.
