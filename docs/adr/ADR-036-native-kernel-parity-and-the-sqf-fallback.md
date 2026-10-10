# ADR-036: Native kernels, parity and the SQF fallback

Status: proposed. This record defines the native kernel architecture: the
SQF-reference-plus-native-optional pattern, the fallback rule, the per-kernel
parity tolerance, the server-versus-client split, the clock dependency and the
licence.

Relates to ADR-017 (engine anchors), ADR-034 (framework architecture),
ADR-035 (truth versus assumption).

---

## Context

The kernel/driver split (ADR-034) makes every physics model a pure function
plus a thin driver. A pure function is the only thing a native extension can
accelerate safely and the only thing a unit test can pin without the engine.

Phase E moves the atmosphere, thermal, ballistic drag and eye kernels into the
dev extension `aee_dev` (ADR-035 trust boundary). The SQF kernel stays the
reference and the fallback.

## The pattern: SQF reference plus native optional

A kernel has two implementations behind one dispatcher name.

- The **SQF kernel** is the reference and the oracle. It is the authority.
- The **native kernel** is a pure function in
  `tools/dev-harness/extension/src/kernels/`. Its numeric coefficients are
  generated from the SQF reference by `tools/gen_kernel_coefficients.py`, so
  the two cannot drift.

The dispatcher `aee_core_fnc_dispatchKernel` calls the native kernel only when
the preInit probe proved the extension ready and the native return is non-empty
with errorCode 0. Otherwise it calls the SQF kernel.

## The fallback rule

The SQF kernel is never removed. An absent, unloaded or errored extension
selects the SQF path. A native kernel runs only after the `cargo test` parity
and the Docker probe pass. This is the rule that keeps the mod correct without
the extension and without a BattlEye whitelist.

## Tolerance

The engine runs SQF numbers in 32-bit. One f32 rounding is about `6e-8`
relative. The default parity bound is `1e-6` relative, one order above a single
f32 rounding so it absorbs a short `pow` or `exp` chain. No kernel uses a
looser relative bound without a written reason.

| Kernel | Native name | Relative bound | Absolute bound | Reason |
|---|---|---|---|---|
| `calculateStationPressure` | `kernel.calculateStationPressure` | `1e-6` | 0 | One `pow`; the f32 default. |
| `calculateRelativeHumidity` | `kernel.calculateRelativeHumidity` | `1e-6` | `0.5` | The output is `round`ed to an integer, so the smallest meaningful bound is one rounding step (`0.5`). |
| `calculateAirDensityKernel` | `kernel.calculateAirDensityKernel` | `1e-6` | 0 | One `exp`; the f32 default. |
| `solveTwoNodeKernel` | `kernel.solveTwoNodeKernel` | `1e-3` | 0 | The 12-iteration nonlinear two-node fixed point amplifies one f32 engine rounding (about `6e-8`) by the Newton gain: the measured engine divergence is of order `1e-5` relative, so the `1e-6` default does not hold. `1e-3` is the ceiling with this written reason. The cargo vectors are f64-to-f64 and pass tighter. |
| `calculateBallisticDrag` | `kernel.calculateBallisticDrag` | `1e-6` | 0 | One `sqrt` and a linear table interpolation; the f32 default. |
| `eyeAdaptStep` | `kernel.eyeAdaptStep` | `1e-6` | 0 | Two `exp` chains; the f32 default. |
| `eyeMesopicWeight` | `kernel.eyeMesopicWeight` | `1e-6` | 0 | Two `log` and a polynomial; the f32 default. |
| `eyePupilSteady` | `kernel.eyePupilSteady` | `1e-6` | 0 | One `log` and one `exp`; the f32 default. |
| `eyePupilStep` | `kernel.eyePupilStep` | `1e-6` | 0 | One `exp`; the f32 default. |
| `eyeTimeSkip` | `kernel.eyeTimeSkip` | `1e-6` | 0 | Comparator only; exact in both paths. |

The Rust `#[test]` `native_kernels_match_the_sqf_reference` reads vectors
generated from the SQF reference by `tools/gen_kernel_vectors.py`. The
interpreter evaluates in 64-bit, so the vectors are the exact formula values
and the cargo test passes with margin. The Docker probes **P137**, **P138** and
**P139** are the engine-truth cross-check: each compares the dispatcher's
answer to the SQF reference in the running engine at the same per-kernel bound.
P139 drives the drag and eye pure kernels directly on the dedicated server,
because a pure kernel needs no player. The kernel's real call sites are
client-local and stay manual `interface` ceilings (ADR-035).

`tools/tests/test_kernel_parity.py` fails when the generated coefficient or
vector file is stale, or when a kernel's relative bound exceeds `1e-6`.

## Server versus client

A pure kernel is server-callable whatever its driver side. The generated kernel
table (`docs/wiki/research/kernel-table.md`) states the driver side per kernel.
The atmosphere, thermal, drag and eye kernels are server-callable and are
proven on the dedicated server (P137, P138, P139). The client-only integrations
- the drag `Fired` call site and the `hasInterface` eye driver - are manual
`interface` ceilings (ADR-035). The extension ships in no release artefact, so
a production client with BattlEye on never loads it. That is the client-kernel
ceiling.

## The clock dependency

A kernel that integrates over time takes a `dt` argument. The `dt` comes from
the one clock (`aee_core_simTime`), never from `diag_deltaTime` (ADR-034). A
throttled model computes `_dt = aee_core_simTime - _lastSimTime` once per run
and passes it to the kernel. The extension owns no time: a kernel is a pure
function of its arguments. The `eyeTimeSkip` kernel compares the world `dayTime`
and handles the 86400 wrap; the clock module supplies the two samples.

## Probe number

The plan named the kernel parity probe `P129`. The branch already used `P129`
for the terrain-look probe, so the kernel parity probe takes the next free
number, `P137`. The plan's `P128` clock number is likewise stale on this branch
(`P135` is the clock probe). The probe bodies, not the plan's numbers, are the
contract.

## The licence

The extension crate is `GPL-2.0-or-later`
(`tools/dev-harness/extension/Cargo.toml`), matching the repository `LICENSE`
and its PBO-distribution exception. The crate is `publish = false` and ships in
no release artefact. The `arma-rs` dependency is used under its own licence; the
crate does not change the repository licence.

## Consequences

- A native kernel runs only after `cargo test` and the Docker probe pass.
- The SQF kernel is never removed; it is the fallback and the oracle.
- The client-only integrations (the drag `Fired` call site and the
  `hasInterface` eye driver) stay manual `interface` ceilings, recorded in
  ADR-035.
