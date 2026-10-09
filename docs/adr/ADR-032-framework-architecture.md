# ADR-032: The framework architecture - a layer on the engine's anchors

Status: proposed. The record is written with the first framework pillars. The
conformance, ownership and observation pillars lean on the existing layer.

Relates to ADR-001 (engine anchors), ADR-011 (nightly headless regression),
ADR-017 (flight physics ceiling), ADR-027 (ownership architecture),
ADR-031 (conformance layer).

---

## Context

Arma 3 exposes a fixed set of anchors. A mod can read and write a config
class, register an event handler, call an SQF command, run a per-frame
handler, and load a native extension. The engine withholds the rest. The
solver is PhysX and cannot be extended. The renderer is closed. There is no
`setFlightModel` and no per-tick force accumulator
(`docs/engine/engine-commands-and-features.md` Part 3, ADR-017).

AEE therefore cannot replace the engine. It can own a deterministic layer of
pure functions over the engine's inputs and outputs. That layer needs one
time base, one split between pure maths and engine access, one place that
publishes state, one rule for who owns a config key, and one proof surface.

Two recent defects forced this record. The eye driver
(`fnc_updateEyeAdaptation`) and the thermal automatic gain control
(`fnc_updateThermalAGC`) broke the same way. Both integrated `diag_deltaTime`
inside a throttled CBA per-frame handler. `diag_deltaTime` is the previous
rendered frame duration, not the handler interval. The CBA handler supplies
no delta. The filter time constant therefore depended on the frame rate. The
eye showed a cone time constant near 16 s against a configured 2 s. One clock
removes that whole class.

## Decision

AEE builds a framework on the engine's anchors. It is never a replacement.
The framework has five pillars.

| # | Pillar | The plain idea |
| --- | --- | --- |
| 1 | One real-time clock | A single authoritative monotonic time source. |
| 2 | The kernel split | Every physics model is a pure kernel plus a thin driver. |
| 3 | The state registry and observation layer | Every published variable is declared once. Every addon exposes a dump. |
| 4 | The anchor and ownership layer | A config change reads the engine first and overrides only our keys. |
| 5 | The conformance layer | Generators with `--check` and one manifest make the framework self-describing. |

The clock is first because a wrong time base corrupts every model downstream.
The kernel split is second because a pure function is the only unit a native
extension can accelerate and the only unit a test can pin without the engine.
The state registry is third because it is how the framework is observed.
Ownership and conformance are the existing layers (ADR-027, ADR-031) that the
framework leans on.

## The defect class, stated once

The defect class is an integration of `diag_deltaTime` inside a throttled CBA
per-frame handler. The eye driver (`fnc_updateEyeAdaptation`, commit
`f36bc216`) and the thermal AGC (`fnc_updateThermalAGC`, commit `fc81d68e`,
probe P79) were the same defect. The filter time constant silently tracked
the frame rate. The engine's commands-and-features reference states that the
CBA per-frame handler supplies no delta
(`docs/engine/engine-commands-and-features.md:425,431-457`).

The rule that closes the class: no model reads `diag_deltaTime` as its
interval inside a throttled handler. A scan fails on any `diag_deltaTime`
read outside the clock module.

## The clock API

The clock module publishes one monotonic variable, `aee_core_simTime`,
advanced from `diag_tickTime`. It does NOT publish a shared per-frame delta.
A throttled model that read a per-frame delta would read about `1/FPS` and
under-integrate again, which is the exact defect.

Each throttled model keeps its own `_lastSimTime` and computes
`_dt = aee_core_simTime - _lastSimTime` once per run. `diag_tickTime` is real
monotonic time. It advances during pause and it ignores `accTime`. That is
correct for the eye and the AGC, which filter real time. A model that needs
simulation time scales by `accTime` explicitly. A clock-jump detector
compares `dayTime`, which jumps on `skipTime`, and handles the 86400 wrap.

## Consequences

- The defect class is removed by construction. A `diag_deltaTime` read
  outside the clock module fails a test.
- A frame-rate probe runs a throttled model at two `limitFPS` settings and
  asserts the same integrated state.
- A pure kernel contains no engine write. A kernel that writes engine state
  fails the split test.
- The framework does not replace the engine's solver, renderer or physics
  step. Those remain the engine's (ADR-017).
- The native extension only accelerates a kernel. It never replaces the
  engine.
- Cost: an extra indirection per throttled model (one last-sample variable)
  and one scan. The scan pays this back by refusing a reintroduced read.

## Manual ceilings

A ceiling is a claim the harness cannot prove from a dedicated-server run. Each
is recorded here so no run reports it as passed.

- **The human eye on a client.** A dedicated server renders nothing, so the
  rendered look is an operator-only observation.
- **The 907 ms first-entry engine build.** The engine pays a one-off build cost
  the first time a model runs. It is a first-entry cost, not a steady-state one.
- **The engine's uncontrollable frame delivery.** A dev tool cannot force a
  frame. The engine delivers frames on its own schedule.
- **The BattlEye-on server path for the client kernels.** A production server
  keeps BattlEye on, so the client kernels run dev-only with BattlEye off.
- **Standards judgement.** A check proves a value carries a source; it cannot
  prove the value is right. Physics fidelity and colour representation are human
  calls.
- **External-truth rebuilds.** A corpus built from the engine or the web needs
  that source present. The gate proves it is unchanged since commit; it cannot
  prove it is still correct without the source.

## References

- `docs/engine/engine-commands-and-features.md` (the per-frame handler and the
  `diag_deltaTime` contract).
- `docs/adr/ADR-017-flight-physics-ceiling.md` (the engine-internal ceiling).
- `docs/adr/ADR-027-ownership-architecture.md` (ownership by declaration).
- `docs/adr/ADR-031-conformance-layer-self-describing-detect-and-repair.md`
  (the conformance layer).
- `addons/core/functions/fnc_updateSimClock.sqf` (the clock).
- `tools/tests/test_sim_clock.py`, `tools/tests/test_sim_clock_guard.py`,
  `tools/tests/test_kernel_split.py` (the pillar gates).
- `addons/optics/functions/eye/fnc_updateEyeAdaptation.sqf` and
  `addons/thermal/functions/solver/fnc_updateThermalAGC.sqf` (the defect).
