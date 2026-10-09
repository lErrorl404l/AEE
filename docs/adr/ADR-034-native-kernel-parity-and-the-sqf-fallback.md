# ADR-034: Native kernels, parity and the SQF fallback

Status: proposed.

Relates to ADR-017 (engine anchors), ADR-032 (framework architecture),
ADR-033 (truth versus assumption).

---

## Context

The kernel/driver split (ADR-032) makes every physics model a pure function
plus a thin driver. A pure function is the only thing a native extension can
accelerate safely and the only thing a unit test can pin without the engine.

Phase E moves the atmosphere, thermal, ballistic drag and eye kernels into the
dev extension `aee_dev` (ADR-033 trust boundary). The SQF kernel stays the
reference and the fallback. The dispatcher
`aee_core_fnc_dispatchKernel` calls the native kernel only when the preInit
probe proved the extension ready and the native return is non-empty with
errorCode 0, else it calls the SQF kernel.

## Decision

A native kernel is a pure function in `tools/dev-harness/extension/src/kernels/`.
Its numeric coefficients are generated from the SQF reference kernel by
`tools/gen_kernel_coefficients.py`, so the two cannot drift. The dispatcher
selects the native path; an absent or errored extension selects SQF.

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
client-local and stay manual `interface` ceilings (ADR-033).

`tools/tests/test_kernel_parity.py` fails when the generated coefficient or
vector file is stale, or when a kernel's relative bound exceeds `1e-6`.

## Probe number

The plan named the kernel parity probe `P129`. The branch already used `P129`
for the terrain-look probe, so the kernel parity probe takes the next free
number, `P137`. The plan's `P128` clock number is likewise stale on this branch
(`P135` is the clock probe). The probe bodies, not the plan's numbers, are the
contract.

## Consequences

- A native kernel runs only after `cargo test` and the Docker probe pass.
- The SQF kernel is never removed; it is the fallback and the oracle.
- The client-only integrations (the drag `Fired` call site and the
  `hasInterface` eye driver) stay manual `interface` ceilings, recorded in
  ADR-033.
