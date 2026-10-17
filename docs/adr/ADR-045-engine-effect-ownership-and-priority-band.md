# ADR-045: Engine effect ownership and the priority band

Status: Accepted
Date: 2026-10-17

Decision: AEE owns every post-process handle it creates, through one of two
scopes, and it records every create site in one ledger. A handle is destroyed
before its variable resets to -1. AEE keeps its priority range of 100 to 6000
and does not copy a priority from a co-installable mod. The engine treats a
priority as both a unique slot and a draw order, so a collision is a
correctness fault, not a cosmetic one.

## Context

A post-process effect is created by `ppEffectCreate`, adjusted by
`ppEffectAdjust`, committed by `ppEffectCommit` and enabled by `ppEffectEnable`.
The engine draws the enabled effects in ascending priority, so a higher
priority renders later, on top of the lower ones
(https://community.bistudio.com/wiki/ppEffectCreate and the Post Process
Effects tutorial).

The AEE stack has 25 engine handles in five owners: the optics and nightvision
registry, the eight thermal display effects, the six night-vision tube effects,
the four fusion effects, and the engine-owned LightShafts advanced effect. The
full table, with a file and line per handle, is in
`.omo/research/engine-truth/aee-pp-ownership.md`.

Vanilla sets its optics effects through `CfgOpticsEffect` in
`A3\data_f\config.cpp`, with priorities banded by effect type: radial 100,
chroma 250, blur 450, grade 1550, grain 2050 and inversion 2550. Vanilla
scripts reach priority 2012. AEE reaches 6000 for the NVG and thermal overlay
chain. The vanilla evidence is in
`.omo/research/engine-truth/vanilla-render-pipeline.md`.

## Decision

1. **Two ownership scopes.** The registry (`addons/lib/functions/
   fnc_createPPEffect.sqf`) serves the `optics` and `nightvision` scopes. The
   direct creators serve thermal display, the NVG tube model and fusion. A
   handle has exactly one owner, one create site and one destroy path. A
   creator that bypasses the registry must still appear in the ledger.

2. **Lifecycle order.** Create, then adjust, then commit, then enable. A
   destroy comes before the variable resets to -1, never after. A commit is
   required for a change to appear. The BIKI tutorial documents create, enable,
   adjust, commit; the difference is deliberate, so the first visible frame
   carries the intended parameters rather than the engine default. The two
   orders are UNVERIFIED as equivalent until a rendered client compares them.

3. **The priority band is 100 to 6000.** It exceeds the vanilla optics ceiling
   of 2550 on purpose: the NVG tube grade at 5100 and grain at 6000 must render
   after the fusion grade at 2505, and the engine applies ascending priority.
   The band is a statement of intent, not a reservation: the engine reserves no
   number, and another addon can hold one first.

4. **A collision is a defect.** The BIKI says a duplicate priority fails
   creation and returns -1. A repository measurement recorded a positive shared
   handle on one build, which would let the first teardown destroy the other
   owner's effect. The two records disagree, so the claim is UNVERIFIED until a
   rendered client creates two effects at one priority and reads both handles.
   Until then, uniqueness is enforced by a committed ledger, not by the engine.
   Do not copy a priority from A3TI, MKK or TFN: a copied value guarantees the
   shared-handle case when that mod is also loaded.

5. **No `CfgOpticsEffect` publication.** AEE drives its optic effects from
   script and publishes no `CfgOpticsEffect` class. The engine therefore cannot
   apply the AEE optic stack, and another mod cannot inherit it. This is a
   recorded gap, not an accident. A future adoption needs its own ADR.

6. **The NVG force flag is not a thermal flag.** `ppEffectForceInNVG` forces an
   effect into the night-vision channel. No documented command forces a
   `ppEffect` into the thermal channel; thermal is reached through
   `setPiPEffect` on a render target. Whether the NVG flag also reaches thermal
   is UNVERIFIED. A thermal overlay must not depend on it.

7. **Advanced effects are name-only.** `LightShafts` and `HBAOPlus` cannot be
   created by `ppEffectCreate`. They are adjusted and enabled by name, and
   their adjustments are immediate and need no commit. `DepthOfField` is not in
   the documented creatable list, though AEE creates and uses it; it is
   UNVERIFIED and a rendered client must settle it.

## Consequences

- Every new effect needs a ledger row, a priority inside the band, and a
  destroy path on each exit: module disable, player death, vision-mode change
  and mission end.
- A handle variable is never set to -1 while the effect is live. A leak is a
  lifecycle fault even when the effect is invisible.
- The static contract tests read the ledger and the source. They need no game.
- The four engine-only claims (the collision return value, the order
  equivalence, the thermal reach of the NVG flag, and the DepthOfField
  creation) stay UNVERIFIED until a rendered client settles them. The static
  tests must not assert them as facts.

## Sources

- `.omo/research/engine-truth/biki-pp-contract.md` sections 1 to 5 and 9.
- `.omo/research/engine-truth/vanilla-render-pipeline.md` sections 1 and 5.
- `.omo/research/engine-truth/aee-pp-ownership.md` sections 1 to 3 and 6.
- `docs/engine/command-surface-3.md` section 1.
