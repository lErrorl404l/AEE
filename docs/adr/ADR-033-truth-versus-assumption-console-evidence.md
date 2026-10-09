# ADR-033: Truth versus assumption - a console result is evidence, not a gate

Status: proposed. This record defines the dev-experience programme and its trust
boundary. It records the extension console, the visual workbench, the batching,
the four-layer gate, the release-artefact exclusion, the truth-versus-assumption
rule, the BattlEye-off client-kernel ceiling and the manual ceilings.

Relates to ADR-011 (nightly headless regression), ADR-017 (engine anchors),
ADR-027 (ownership architecture), ADR-031 (conformance layer), ADR-032
(framework architecture).

---

## Context

The dev console runs SQF in a live session and returns a result to the
developer. That result is an observation of one session. It cannot be
reproduced by CI: CI has no engine, no live session and no network.

A gating fact must be reproducible. A console-only result that gated CI would
depend on a live session CI cannot create, so the gate would fail open or need a
manual step. A result a developer saw once is evidence, not a gate.

## The programme

The dev-experience programme has four parts.

1. **The extension console.** A dev-only native extension, `aee_dev`, listens on
   loopback only. It runs SQF in a live session, reads a `missionNamespace`
   variable, dumps a subsystem, drives a scenario and runs a batch of probes. It
   reaches SQF through the `ExtensionCallback` mission event handler; SQF
   answers through `callExtension`.
2. **The visual workbench.** Four keybinds under the `AEE Dev` category
   re-apply a `setObjectTexture`, `setObjectMaterial` or `ppEffectAdjust`
   change at run time, take a labelled screenshot and dump the state, so a
   visual change is seen without a relaunch.
3. **Test batching.** One live session runs many probes. Each probe has a run
   class (`headless`, `headless-client`, `interface`). The runner reports
   `client-unavailable` for a probe the machine cannot carry, and it never
   reports a client probe as passing from a server-only run.
4. **The native kernels.** Phase E moves the atmosphere, thermal, ballistic drag
   and eye kernels into the extension. The SQF kernel stays the reference and
   the fallback (ADR-034).

## The four-layer gate

The channel exists only when four independent layers hold. All four must hold.

1. **Build-time exclusion (structural).** The dev project is a standalone HEMTT
   project outside `addons/` and `optionals/`. The main project's `hemtt build`
   and `hemtt release` cannot see it.
2. **Addon-load exclusion.** The release mod list does not name the dev mod. The
   harness PBO is a separate mod folder, not inside the release mod.
3. **Run-time gate.** The poller starts only when file patching is active, the
   sentinel file exists, and the host is a dev host.
4. **No arbitrary code.** The command surface is a fixed verb table. The only
   `compile` is the gated `eval` verb, which is reachable only on a fully gated
   dev session.

When a layer fails, the channel does not exist. There is no handler, no verb and
no log line. The failure is a silent no-op.

## The release-artefact exclusion

The dev surface ships in no release artefact.
`tools/tests/test_dev_harness_release_exclusion.py` proves it on the RELEASE
tree, not only on `.hemttout/build`: the tree named by `AEE_RELEASE_TREE`
carries no `aee_dev.pbo`, no dev `.so`/`.dll` and no `[AEE][dev]` marker. The
proof runs as a CI/phase gate after `hemtt release`, not in the per-commit
`run_tests.py --fast` set.

## Decision (the truth-versus-assumption rule)

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

## Relationship to ADR-027 and ADR-031

- **ADR-027 (ownership architecture).** The console observes published state and
  calls published functions; it names no key it does not own. The `set` verb
  refuses a variable name that is not ours. The extension reads the same `aee_*`
  contract a third-party mod reads.
- **ADR-031 (conformance layer).** The console, the workbench and the generators
  are part of the conformance layer's self-describing surface. The `--check`
  generators make each contract a projection, not a second copy
  (`tools/gen_dev_console_contract.py`, `tools/gen_kernel_table.py`). The
  dev-experience gates are registered with the rest.

## Consequences

- A developer sees a fact live and gets a verdict immediately.
- CI stays network-free and engine-free (ADR-011 nightly regression).
- A gating fact carries two artefacts: the console observation and the probe.
- The dev surface cannot leak into a release: the exclusion is structural and
  proven on the release tree.

## Manual ceilings

A ceiling is a claim the harness cannot prove from a dedicated-server run. It is
recorded here and never reported as passed by a server-only run.

### The human eye on a client

The rendered look is a manual ceiling. A dedicated server renders nothing, and
no automated gate reads a pixel. The operator presses the re-apply keybind,
looks at the result and confirms the change. The screenshot is evidence for that
manual check, not a gate.

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
