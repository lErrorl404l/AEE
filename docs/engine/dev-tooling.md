# Dev tooling and the engine

The development surface reads engine state and calls engine commands. It obeys
the same rule as a config change: read the engine first, then change. This note
records that rule and its ceilings.

## The rule

Before a change to a dev tool that touches the engine:

1. Read the engine's own behaviour for the anchor. Do not guess.
2. A dev tool holds no engine state. It observes published state and calls
   published functions.
3. The engine keeps the solver, the renderer and the physics step. The dev tool
   builds on the anchors only (ADR-017, ADR-032).
4. A dev tool that needs a new engine anchor records a ceiling here first.

## The surface

The dev console is a loopback-only native extension. The visual workbench
re-applies a `setObjectTexture`, `setObjectMaterial` or `ppEffectAdjust` change
at run time. The native kernels are pure functions the extension accelerates.
The SQF kernel stays the reference and the fallback (ADR-034).

## Ceilings

- The dev surface ships in no release artefact. A production client keeps
  BattlEye on, so a client never loads the extension (ADR-033).
- The render is a manual ceiling. A dedicated server renders nothing, so a
  rendered verdict is a human call.
- The engine delivers frames on its own schedule. A dev tool cannot force a
  frame.
- The `diag_deltaTime` value is the previous rendered frame duration, not a
  handler interval. One clock module owns it (ADR-032).

## Related records

- `docs/wiki/chapters/dev-console.qmd` - the operator-facing chapter.
- `docs/adr/ADR-032-framework-architecture.md` - the framework.
- `docs/adr/ADR-033-truth-versus-assumption-console-evidence.md` - the trust
  boundary.
- `docs/adr/ADR-034-native-kernel-parity-and-the-sqf-fallback.md` - the kernels.
