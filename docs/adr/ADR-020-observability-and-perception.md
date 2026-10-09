# ADR-020: Observability and perception - the debug index, the perception monitor and the consistency harness

Status: Accepted

## Context

AEE publishes state in many modules. The state was readable only by a person
who knew each variable name. The per-module log lines had no shared shape, so
a person could not read one line and see the whole module. A cross-module
disagreement was invisible: two modules could compute the same quantity and
disagree, and no code compared them.

The human-vision model and the eye adaptation already lived in the optics module, now `addons/eye` and `addons/vision`.
The observability work added a perception aggregate, a runtime monitor and a
consistency harness. The work needed a home.

One option was a new PBO for the perception work. A new PBO carries a new
signed artefact, a new load order and a new release step. The work did not
need that weight.

## Decision

### No new PBO

The perception work lives in `addons/vision`. The consistency and module-health
work lives in `addons/diagnostics`. No new addon directory is created, so the release
ships no new PBO.

### The optics home

The perception state lives in `addons/vision`. The pure kernel
`perceptionSample` and the client driver `perceptionUpdate` sit under
`functions/perception`. The driver publishes `aee_vision_perceptionState` and
its named fields: line, lux, aperture, grade and flags. The debug surface adds
the force hooks and the settings under **AEE Debug > Perception**.

### The core home

The module-health report and the consistency monitor live in `addons/diagnostics`.
The evaluator `evaluateConsistency` is a pure kernel. The invariant table is
`data/consistency/invariants.json`. The monitor publishes
`aee_core_consistencyState`, `aee_core_consistencyFailures` and
`aee_core_consistencyLast`. The module-health report publishes
`aee_core_moduleHealth`.

### The pure-kernel boundary

`perceptionSample` and `evaluateConsistency` read no world state, no module
global and run no engine command. The caller supplies a value map. The kernel
returns a fixed-length array in a documented schema order. A HashMap is not
accepted as input, because reading one needs the `get` engine command. The
value map is a flat array of key and value pairs.

This boundary lets the same kernel run in the game client, in an AI caller and
in a headless probe. The kernel is testable without the engine.

### The AI entry point

An AI has no render state and no camera. The AI calls
`EFUNC(vision, perceptionSample)` with its own value map. The kernel returns
the same fixed schema that the client driver reads. The AI path does not read
the local player state, so it is valid on a server. This is the reason the
kernel lives in `addons/vision` and not in a client-only display path.

### The settings and the hooks

The monitor adds three settings under **AEE Debug > Perception**:
`perceptionMonitor`, `perceptionHud` and `perceptionInterval`. The monitor
adds four `missionNamespace` force hooks for the debug console:
`perceptionForceLux`, `perceptionForceGrade`, `perceptionForceNvg` and
`perceptionForceThermal`. The consistency monitor adds three settings under
**AEE Debug > Consistency**: `consistencyCheck`, `consistencyInterval` and
`consistencyStrict`.

### The honest limits

A dedicated server has no local player and no client render state. The
perception monitor therefore publishes nothing there. The monitor self-gates
on `hasInterface` and on a living local player. A server cannot read the
client render state, so the perception state is a client value.

A headless probe cannot read pixels. The probes verify the pure kernels, the
published state and the config keys. The pixel look stays an operator-owned
observation.

### The future split

If the perception capability outgrows `addons/vision`, split a future
`addons/perception`. The pure-kernel boundary makes the move cheap, because
the kernel reads no optics global and no engine command. The move is an open
option, not a commitment.

## Alternatives rejected

- A new PBO for the perception work. It adds a signed artefact, a load order
  and a release step for no functional gain.
- A server-side perception monitor. A server cannot read the client render
  state, so the monitor would publish a value it cannot compute.
- Reading the world inside the kernel. It would bind the kernel to the engine
  and block the AI caller and the headless probe.
- A HashMap as the kernel input. Reading one needs the `get` engine command,
  which the pure boundary forbids.
- A second copy of the perception schema in the AI module. Two copies drift.
- A separate consistency addon. The evaluator reads published state only, so
  it belongs with the core orchestrator.

## Consequences and ceiling

- The debug index is generated from the source, so a new module row appears
  without a hand edit.
- The perception kernel is pure, so one fixture set covers the client driver,
  the AI caller and the probe.
- The consistency harness compares published state only. A module that
  publishes no value is marked `no-data`, not failed.
- The perception state is client only. A dedicated server cannot read it.
- The pixel look of the perception overlay and the felt eye adaptation stay
  operator-only.
- The future `addons/perception` split stays open until the capability needs
  it.
