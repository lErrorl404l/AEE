# ADR-008: Night-Sky Render Primitives

Status: Accepted
Date: 2026-10-04
Decision: The aurora, the Milky Way and the faint star bulk are drawn with engine primitives that consume no dynamic light. The aurora is a particle curtain, the Milky Way is an immediate-mode line band, and the faint stars are a capped immediate-mode layer. Each feature has a force hook and reports its state in one log line.

## Context

The operator could not see the aurora, the Milky Way or a meteor shower. The
RPT showed the starfield drawing 261 to 3491 stars but always only 26 light
emitters, the meteor worker logging no spawn for six minutes, and no aurora or
Milky Way line at all.

The engine caps concurrent dynamic lights, and the bright stars already use
that budget. A render primitive that takes a dynamic light per element cannot
carry a band, a curtain or a faint field of thousands of stars. A render
primitive that costs no dynamic light can.

## Decision

1. **Aurora: particle curtain.** The worker draws the space-weather aurora
   state as one or two `#particlesource` curtains in the northern sky. The
   green and red colours derive from the 557.7 nm and 630.0 nm oxygen lines.
   The particle texture is the vanilla `\A3\data_f\cl_basic` already used by
   the meteor trail. The geometry is a render tunable and is labelled
   UNSOURCED.

2. **Milky Way: immediate-mode band.** The sampler walks 96 points along
   galactic latitude 0, projects each through the galactic kernels, and the
   Draw3D worker draws consecutive pairs with `drawLine3D`. The band follows
   the sidereal motion with the starfield. The brightness is anchored to the
   published dark-sky surface brightness; every render tunable is UNSOURCED.

3. **Faint stars: capped immediate-mode layer.** The light-emitter path caps
   at `STAR_LIGHT_MAX_MAG`. A separate Draw3D worker draws the fainter
   catalogued stars as short line segments, capped at `FAINT_STAR_MAX`. It
   consumes no dynamic light, so the light cap no longer hides the field.

4. **Rejected: `ppEffect` and a sky-dome texture.** No creatable `ppEffect`
   draws a moving band or a curtain with the sidereal motion, and a new
   texture asset is out of scope. The engine primitives need no new asset.

5. **Dynamic-light reasoning.** The light cap is about 32 (a third-party
   statement, not an official figure) and is treated as a cautious ceiling.
   The design keeps the light-emitter path for the bright stars only and
   gives every other element an immediate-mode or particle path.

## Consequences

- **Good**: The aurora, the Milky Way and the faint stars render without
  competing for the dynamic-light budget. Every feature is forceable and
  reports its state in the `sky state` line.
- **Cost**: The faint-star cap and the band sample count bound the per-frame
  cost. The Milky Way brightness needs operator tuning.
- **Risk**: The render primitives need an in-game check. The operator owns
  that check.

## References

- Plan: `.omo/plans/aee-night-sky-debug.md`.
- NOAA SWPC Aurora Tutorial: the 557.7 nm and 630.0 nm oxygen lines.
- Crumey 2014 (via Wikipedia "Surface brightness"): dark-sky surface
  brightness 21.8 mag/arcsec^2.
- IAU 1958 galactic system (Blaauw et al. 1960): the galactic frame constants.
- Reid and Brunthaler 2004: Sgr A* J2000 (the kernel test anchor).
- BI wiki: `#particlesource`, `setParticleParams`, `drawLine3D`.
