# ADR-033: Truth versus assumption - a console result is evidence, not a gate

Status: proposed. This records the truth-versus-assumption rule. It is a stub:
task 36 (the manual ceiling record) expands it with the full ceiling table.

Relates to ADR-011 (nightly headless regression), ADR-017 (engine anchors),
ADR-031 (conformance layer), ADR-032 (framework architecture).

---

## Context

The dev console runs SQF in a live session and returns a result to the
developer. That result is an observation of one session. It cannot be
reproduced by CI: CI has no engine, no live session and no network.

A gating fact must be reproducible. A console-only result that gated CI would
depend on a live session CI cannot create, so the gate would fail open or need a
manual step. A result a developer saw once is evidence, not a gate.

## Decision

1. A console result is evidence. It records what one live session did. It is
   never a gate.
2. A fact that must gate also gets a probe file with its own `[Pxx]` tag and an
   entry in `tests/docker/verify.py`. The gate is the probe, run by the Docker
   harness, not the console call.
3. The console `probes` op reuses the probe tags and file names, so a console
   fact and its gating probe are one fact observed two ways
   (`fnc_devProbeManifest` is the single manifest).
4. `tools/tests/test_console_fact_gating.py` enforces the rule: every
   `[Pxx]`-tagged console fact names a probe file that exists, a `headless`
   console fact has a `verify.py` gate, and a `headless-client` or `interface`
   console fact has no server-side gate.
5. A console-only result must not gate CI. Only the registered unit suites and
   the Docker probe gate block a change.

## Consequences

- A developer sees a fact live and gets a verdict immediately.
- CI stays network-free and engine-free (ADR-011 nightly regression).
- A gating fact carries two artefacts: the console observation and the probe.

## Manual ceilings

A ceiling is a claim the harness cannot prove from a dedicated-server run. It is
recorded here and never reported as passed by a server-only run.

### BattlEye-off client-kernel ceiling

The dev extension `aee_dev` runs on a client only with BattlEye off (it is
dev-only and ships in no release artefact, ADR-033). A production client keeps
BattlEye on, so the native client path is never exercised in production. The
parity fact is proven by the pure kernels, which are server-callable: the
dedicated server drives each kernel directly (P137, P138, P139) with no player
and no BattlEye interaction. The dispatcher's client use of the same kernels is
therefore a manual ceiling.

### Drag `Fired` call-site ceiling (interface)

The drag kernel `aee_ballistics_fnc_calculateBallisticDrag` is pure and
server-callable. Its real call site, `fnc_resolveShot` from the client-local
`Fired` event handler (`addons/ballistics/XEH_postInit.sqf`), runs only on a
machine with an interface. That integration is a manual `interface` ceiling:
P139 proves the kernel headless, and no server-only run claims the `Fired`
integration passed.

### Eye `hasInterface` driver ceiling (interface)

The eye kernels (`eyeAdaptStep`, `eyeMesopicWeight`, `eyePupilSteady`,
`eyePupilStep`, `eyeTimeSkip`) are pure and server-callable. Their driver,
`fnc_updateEyeAdaptation`, is gated on `hasInterface`
(`addons/optics/functions/eye/fnc_initEyeAdaptation.sqf:16` and
`addons/optics/XEH_postInit.sqf`), so it runs only on a machine with an
interface. That integration is a manual `interface` ceiling: P139 proves the
kernels headless, and no server-only run claims the driver passed. The driver
is NOT a `headless-client` fact; a dedicated server and a headless client both
report `hasInterface = false`.
