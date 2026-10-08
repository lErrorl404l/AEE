# ADR-027: Ownership architecture, declared sovereignty

Status: accepted.

## Context

The operator's principle: AEE overhauls and extends the base game with real
physics, biology and chemistry, "dynamically overwriting and taking control of
any/all classes and code, owning the runtime so that any other custom mod uses
our information and our details instead of them taking control over us",
allowing client-side mods, and owning what AEE changes.

Three facts bound what "own the runtime" can mean.

**Config is load-time and global.** A PBO's config merges into the engine's
config tree when the PBO loads. The merge is last-loaded-wins per property. No
script command writes the config tree for the classes in question.
`CfgAmmo airFriction` is sampled when a projectile is created, but the value
itself is fixed at load. The PBO is the only off switch (ADR-001).

**Script state is runtime, per-machine, last-writer-wins.** CBA's `PREP`
compiles each function to a global named `aee_<component>_fnc_<name>`. ACE uses
the same scheme with the `ace_` prefix. There is no ownership flag, no priority
and no arbitration. Whoever assigns the variable last wins.

**The engine's C++ runtime is not addressable by either mechanism.** The
simulation solver, the renderer, the flight dynamics model, the ballistic
integrator and the AI routing are closed (ADR-017). A mod reaches them only
through config values the engine reads at load and through commands the engine
exposes.

AEE today re-declares eleven engine classes in place and has one compat layer,
`compat_ace3`, written as AEE adapting to ACE.

## Decision

AEE owns by declaration and load order, not by force. This is declared
sovereignty.

1. **Config ownership.**
   (a) Over the base game: AEE declares the base addons in `requiredAddons[]`.
   The base game always loads first, so every class AEE re-declares wins. Keep
   this.
   (b) Over another mod that touches the same class: a per-host optional compat
   PBO that requires the host, re-declares the contested classes, and carries
   `skipWhenMissingDependencies = 1`. This is the pattern ACE ships in
   `ace_compat_aegis`; AEE's `compat_*` PBOs already carry both fields. Over an
   undeclared mod the merge cannot be guaranteed, because only mod-list order
   decides it. That is a ceiling to detect and log, not a defect to chase.
   (c) Another mod extends AEE deliberately: it declares
   `requiredAddons[] = {"aee_core"}` and loads after. AEE treats `aee_*` class
   and function names as a stable public contract and keeps its extension
   registries. The physiology resolvers are the template: `compat_ace3`
   registers into `aee_physiology_massResolvers` and
   `aee_physiology_categoryResolvers`, and the core reads them and never names
   ACE.

2. **Runtime ownership.**
   - AEE owns its own functions absolutely. The
     `aee_<component>_fnc_<name>` namespace plus `PREP` is correct. Nothing
     external writes an `aee_*` global. The prefix is the guard.
   - To take over a host function, in order, stop at the first that works:
     the host's public API (the default; `compat_acre2` calls
     `acre_api_fnc_setCustomSignalFunc`, `compat_acm` calls
     `ace_medical_vitals_fnc_addSpO2DutyFactor`); then a version-guarded
     wrapper that captures the original and calls it, only inside the host's
     compat PBO, never from `aee_core`.
   - `FUNC` and `EFUNC` are a naming convention, not protection. Treat every
     host function as patchable and fragile. Prefer the public API.

3. **The compat policy is per domain, not blanket.** AEE forces the host to
   stand down where AEE is the declared authority: weather, where AEE disables
   `ace_weather_enabled` because AEE owns the weather simulation. AEE adapts to
   the host where the host owns the subsystem: medical vitals, radio hardware,
   arsenal. `compat_ace3` already embodies both directions. Split it by
   direction and name the direction per function, recorded in
   `docs/wiki/chapters/integrations.qmd`.

4. **Detect the silent loss.** At init, read a sentinel property from each
   owned class and log a mismatch, wired into `fnc_dumpState`. Assert each
   compat host is present and log when `skipWhenMissingDependencies` masks a
   renamed host.

5. **Ceilings recorded.** The engine C++ internals are unreachable. Config is
   load-time with no runtime gate, and the PBO is the switch. Priority over an
   undeclared mod is not guaranteeable. A competitor's script namespace cannot
   be taken over without breaking it. `requiredVersion` gates the engine
   version, not a mod version. What must remain client-side is everything the
   engine computes per machine: the NVG overlay, optics and post-process
   effects, wildlife ambience, local sound, the HUD, map and marker rendering,
   and eye adaptation.

## Consequences

- AEE wins every domain it declares, over the base game and over a known host,
  without breaking hosts and without breaking the standalone core.
- Another mod consumes AEE by a one-way dependency, mirroring what
  `compat_ace3` does to ACE.
- Cost: one compat PBO per contested host, and a direction audit per compat
  function.
- Risk: silent load-order loss; a bare class reopen strips inheritance, so keep
  the generated-header guard; function-override breakage on a host upgrade, so
  wrap and version-guard.
- `compat_ace3` becomes ACE adapting to AEE where AEE owns the domain, and AEE
  adapting to ACE where ACE owns it.

## References

- ADR-001 engine anchors: the three override mechanisms and the load-time
  ceiling.
- ADR-017 flight physics ceiling.
- `docs/wiki/research/engine-override-surface.md`: the class-by-class override
  study.
- `docs/architecture/addon-dependencies.md`: the one-way edge map.
- ACE `ace_compat_aegis`: the per-host optional PBO pattern.
