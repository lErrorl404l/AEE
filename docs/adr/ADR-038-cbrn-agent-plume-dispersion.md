# ADR-038: CBRN Agent Plume Dispersion

Status: Accepted
Date: 2026-10-10
Decision: AEE models wind-borne CBRN agent dispersion with the Gaussian plume
and puff equations on the Briggs dispersion coefficients and the Pasquill
stability class, publishes the exposure state, and reuses the existing wind
and CBRN protection models rather than adding a second copy of either.

## Context

AEE had CBRN surface contamination (the Arrhenius Q10 persistence in
`addons/persistence`) and CBRN protective equipment (`fnc_getCbrnProtection`),
but no model of where a released agent travels in the air or how much a
soldier inhales. The scent-dispersion model (`fnc_calculateScentDispersion`)
is a 0..1 detectability heuristic, not a concentration model.

The environment tick already publishes the inputs a dispersion model needs:
wind speed and direction, solar radiation, temperature, humidity and rain.
The Pasquill stability class and the Briggs dispersion coefficients are then
a direct derivation of that state.

## Decision

1. The dispersion physics lives in `addons/weather` (component `weather`),
   the atmospheric-transport owner, in a new `dispersion/` category beside
   the scent-dispersion kernel. It is the sibling of the scent model.

2. The kernels are pure functions, executed by the `sqf_lite` harness in the
   test suite:
   - `fnc_getStabilityClass` - Pasquill A..F from the day/night tables or a
     measured gradient (Turner AP-26 Table 1).
   - `fnc_getDispersionCoefficients` - Briggs rural/urban sigma_y, sigma_z.
   - `fnc_calculatePlumeConcentration` - the steady Gaussian plume with
     ground reflection (Turner AP-26 eq. 3.3).
   - `fnc_calculatePuffConcentration` - the instantaneous Gaussian puff.
   - `fnc_calculateCbrnDecay` - first-order decay from the agent half-life.
   - `fnc_getCbrnAgent` - the FM 3-11 Table 4-1 agent parameters.
   - `fnc_calculateCbrnDose` - the inhalation dose and the LCt50 thresholds.

3. `fnc_updateCbrnPlume` is the driver: it reads the active release, the
   wind state and the rain, computes the ground-level concentration at the
   local unit, accumulates the dose and publishes the exposure state. The
   core environment tick calls it once per tick.

4. Reuse, not duplication. The driver reads the existing wind state
   (`aee_core_currentWind`) and the existing CBRN protection factor
   (`aee_persistence_fnc_getCbrnProtection`). It adds no second wind model
   and no second protection model. The intrinsic atmospheric decay (the
   FM 3-11 agent half-life) is distinct from the existing Arrhenius model,
   which owns the environmental scaling of SURFACE contamination.

5. Off by default. The `aee_weather_CbrnPlumeEnabled` setting gates the
   driver, so an ordinary mission pays nothing. A mission opts in with
   `aee_weather_fnc_startCbrnRelease`.

6. Every value is grounded in a named source. The one UNSOURCED value is the
   numeric solar-flux proxy for the standard's qualitative insolation bands,
   and the engine-rain to mm/h mapping; both are marked in the source.

## Consequences

- A release now produces a concentration and a dose that a medical or ACM
  consumer can read from `aee_core_cbrnPlumeConcentration`,
  `aee_core_cbrnPlumeDose`, `aee_core_cbrnPlumeLethal` and
  `aee_core_cbrnPlumeIncapacitated`.
- The visual plume (particles) is not part of this decision; the model
  publishes the state a future particle effect would render.
- The agent half-lives and the LCt50 values are the FM 3-11 figures. A
  later agent addition extends `fnc_getCbrnAgent` with a cited row.

## References

- Turner, Workbook of Atmospheric Dispersion Estimates, EPA AP-26 (1970).
- Briggs, Diffusion Estimation for Small Emissions, ATDL (1973).
- FM 3-11, Chemical Operations (2003), Table 4-1.
- ADR-002 (facts only) and ADR-003 (the source hierarchy).
