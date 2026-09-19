#include "..\..\script_component.hpp"

/*
Naked-eye limiting magnitude (NELM) from ambient illuminance and
atmospheric seeing.

Model:
  NELM = mBase - seeingPenalty

  mBase = 6.5 - log10(ambientLux / 0.001)
    Starlight (0.001 lux) -> 6.5  (pristine dark sky, Bortle 1-2)
    Crescent  (0.01 lux)  -> 5.5  (Bortle 3-4)
    Gibbous   (0.1 lux)   -> 4.5  (Bortle 5)
    Full      (0.3 lux)   -> 4.0  (Bortle 6)

  seeingPenalty = 0.2 + 1.3 * (seeing - 0.1) / 0.9
    Seeing 0.1 (excellent) -> 0.2 mag penalty
    Seeing 1.0 (terrible)  -> 1.5 mag penalty

Reference: Garstang (2000) empirical NELM-sky brightness relation,
Bortle scale calibrations, Fried (1966) seeing model.

Stores: QGVAR(limitingMagnitude) as scalar.
Returns: limiting magnitude (higher = fainter stars visible).
*/

params [
    ["_ambientLux", 0.001, [0]],
    ["_seeing", 0.5, [0]]
];

// ─── Base NELM from sky brightness ─────────────────────────────────────────
// Linear in log-lux.  Each 10x increase in ambient lux reduces the
// faintest visible star by 1 magnitude.  This matches Garstang's
// empirical NELM-sky brightness relation across the full range from
// starlight to full moon.
private _mBase = 6.5 - log (_ambientLux / 0.001 max 1e-6);

// ─── Atmospheric seeing penalty ───────────────────────────────────────────
// Turbulence degrades point-source contrast.  Stars scatter into larger
// Airy disks, reducing peak brightness against the sky background.
// Linear interpolation between excellent (0.1) and terrible (1.0) seeing.
private _clampedSeeing = _seeing max 0.1 min 1.0;
private _seeingPenalty = 0.2 + 1.3 * ((_clampedSeeing - 0.1) / 0.9);

// ─── Total limiting magnitude ──────────────────────────────────────────────
private _mLim = _mBase - _seeingPenalty;
_mLim = _mLim max 2.0 min 7.0;

missionNamespace setVariable [QGVAR(limitingMagnitude), _mLim];

_mLim
