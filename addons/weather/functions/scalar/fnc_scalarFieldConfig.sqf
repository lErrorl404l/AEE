#include "..\..\script_component.hpp"

/*
Scalar-field descriptors (issue #116).  PURE: it returns a constant table and
reads no engine state.

Each row describes one advected field driven by FUNC(updateScalarFields):

  0: key              (STRING) field name, the registry and store key
  1: depositionV      (NUMBER) dry-removal velocity v_d, m/s
  2: rainScavengeK    (NUMBER) rain washout coefficient, per unit rain rate
  3: sourceMode       (STRING) "registry" (emitter cells) or "background"
  4: windThreshold    (NUMBER) wind speed that starts a background source, m/s
  5: hotFraction      (NUMBER) a cell is "hot" above this fraction of the max

The two v1 fields are smoke and dust.  Gas and CBRN are NOT here: their
dispersion models are owned by issue #105 (CBRN plume) and issue #120 (dense
gas).  They register their own fields and emitters through
FUNC(scalarAddSource) so this engine stays the single advection core.

Value sources:

  smoke depositionV 0.002 m/s - the dry-deposition velocity of fine aerosol
    (sub-micron to a few microns).  Sehmel 1980, "Particle and gas dry
    deposition: a review", Atmospheric Environment 14, 983-1011, gives
    measured v_d of order 1e-3 to 1e-2 m/s for fine aerosol; 0.002 is the
    low-micron end.

  dust depositionV 0.032 m/s - the Stokes settling velocity of a 20 micron
    particle with density 2650 kg/m3 in air:
      v_s = d^2 (rho_p - rho_a) g / (18 mu)
          = (20e-6)^2 * (2650 - 1.2) * 9.80665 / (18 * 1.81e-5)
          = 0.0319 m/s
    Stokes drag and the settling-velocity form: Batchelor 1967, "An
    Introduction to Fluid Dynamics"; also the standard aerosol text Hinds
    1999, "Aerosol Technology", 2nd ed, section 5.  Air dynamic viscosity
    mu = 1.81e-5 Pa.s at 15 C (Hinds 1999, Table 4.1).

  smoke rainScavengeK 3.0 - the repo's own smoke model (issue #10,
    addons/optics/functions/sensor/fnc_calculateSmokePersistence.sqf) applies
    the washout multiplier 1 / (1 + rain * 3).  This engine reuses that sink
    rather than re-deriving it, so the rain removal of smoke is unchanged.

  dust rainScavengeK 2.0 - the repo's own dust model
    (addons/weather/functions/terrain/fnc_calculateDustSuppression.sqf)
    suppresses dust by rain * 2.  Reused.

  dust windThreshold 5 m/s - the repo's atmospheric-dust gate
    (addons/particles/functions/particle/fnc_particleEmission.sqf uses
    windFactor = ((wind - 5) / 15) clamped to [0, 1]).  Reused.

  hotFraction 0.35 - a STATED modelling threshold, not a measured constant.
    A cell counts as "hot" (a candidate particle source) above 35 per cent of
    the field's current peak.  UNSOURCED.

Return:
  ARRAY of field descriptors.
*/

[
    // key,     v_d,   kScav, sourceMode,   windThreshold, hotFraction
    ["smoke",  0.002, 3.0,   "registry",   0,             0.35],
    ["dust",   0.032, 2.0,   "background", 5,             0.35]
]
