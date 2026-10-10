# ADR-038: Weather Fronts as a Bergen State Machine

Status: Accepted
Date: 2026-10-10
Decision: AEE models a mid-latitude weather front as a deterministic Bergen
life-cycle state machine that perturbs the existing atmospheric state. It does
not add a second model of the temperature, pressure or wind physics.

## Context

Issue #15 asks for a dynamic weather front. The issue carries the research:
cold, warm, occluded and stationary fronts, the passage signature of each, and
the Bjerknes (1919) Norwegian cyclone life cycle. The engine cannot draw a
front line on the map. The reachable effect is a forcing on the atmospheric
state that AEE already computes.

The repository computes the atmospheric state in `aee_atmos` and
`aee_weather`. Each kernel is pure and a single tick in
`addons/core/functions/fnc_updateEnvironment.sqf` calls them in order. A front
that recomputed temperature or pressure would be a second model of the same
physics and the two models would drift.

## Decision

1. One front is modelled as a line that sweeps across the map. Its bearing
   follows the prevailing westerlies. The seed offsets the life cycle and the
   bearing, so two missions do not share a front.

2. The front state is a PURE function of mission time and the seeded
   progression (`fnc_calculateWeatherFront`). Every machine computes the same
   front. Nothing is broadcast, so the rule against `publicVariable` holds.

3. The signed distance from the observer to the front line maps to a phase
   factor in [-1, +1] (`fnc_calculateFrontDistance`, `fnc_calculateFrontPhase`).
   One factor drives the whole passage signature.

4. `fnc_updateWeatherFront` applies the factor to the existing state:

   - temperature: the contrast step, `warmSide * f * contrast / 2`
   - pressure: the trough at the line, `-trough * (1 - |f|)`
   - wind: the clockwise veer, published for `fnc_updateWind`
   - cloud trend: the building or clearing term, published for
     `fnc_calculateCloudDevelopment`
   - precipitation: the frontal rate and phase

   The pressure step runs before `fnc_calculatePressureTrend`, so the existing
   3-hour trend ring buffer reports the fall, the trough and the rise of a
   passage. There is no second trend model.

5. The whole front is gated on the computed weather. In Real Weather mode the
   mission supplies the temperature and pressure, so the front stays off.

## Ceiling

The engine `wind` command keeps the base vector. The front veer reaches AEE's
wind consumers only. Pushing the veered value with `setWind` would feed back
through `fnc_updateWind`, which reads the engine wind every tick, and the
rotation would compound. The evidence records this ceiling.

## Consequences

The per-stage numbers come from the issue's research (FAA Advisory Circular
00-6B ch 10.3, WW2010, NOAA JetStream, UK Met Office). The cloud-trend
magnitudes and the bearing spread are modelling choices and are marked
UNSOURCED in the source. A later change can read the published front state to
draw the front on the map, if the engine surface allows it.
