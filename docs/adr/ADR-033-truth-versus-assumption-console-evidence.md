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
