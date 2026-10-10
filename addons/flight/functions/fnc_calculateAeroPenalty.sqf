#include "..\script_component.hpp"

/*
Lift-loss and drag-rise penalties from air density and airframe icing.

These are the two AEE states that had no flight consumer: the published air
density that drives aee_flight_currentLiftRatio, and the FAR 25 Appendix C
icing severity aee_atmos_airframeIcing.  This kernel turns them into bounded
aerodynamic penalties a caller applies with addForce.

DENSITY.  Lift is proportional to air density.  The denominator is ISA
sea-level, AERO_ISA_SEA_LEVEL_DENSITY (AERO_ISA_SEA_LEVEL_DENSITY kg/m3, ISO 2533).  Thin air
removes lift; dense air is not credited here, because the engine's own model
already gains from it.  The term is bounded to AERO_DENSITY_LIFT_LOSS_MAX.

ICING.  FAR 25 Appendix C describes where and how fast ice accretes, not how
much lift it destroys.  AERO_ICE_LIFT_LOSS_MAX and AERO_ICE_DRAG_RISE_MAX
are therefore UNSOURCED modelling choices.  They are bounded, and the
combined lift loss is capped at AERO_LIFT_LOSS_CAP, so the airframe cannot
be stalled by the scripted layer.

Arguments:
  0: NUMBER - lift ratio rho / AERO_ISA_SEA_LEVEL_DENSITY, or 1.0 for sea-level standard day
  1: NUMBER - icing severity, 0..1

Return Value: ARRAY - [lift-loss fraction, drag-rise fraction], both >= 0
Example: [0.9, 0.5] call aee_flight_fnc_calculateAeroPenalty
Public: No
*/

params [
    ["_liftRatio", 1.0, [0]],
    ["_iceSeverity", 0, [0]]
];

private _rhoRatio = _liftRatio max 0;
private _densityLiftLoss = (1 - _rhoRatio) max 0 min AERO_DENSITY_LIFT_LOSS_MAX;

private _ice = (_iceSeverity max 0) min 1;
private _iceLiftLoss = _ice * AERO_ICE_LIFT_LOSS_MAX;

private _liftLoss = (_densityLiftLoss + _iceLiftLoss) min AERO_LIFT_LOSS_CAP;
private _dragRise = _ice * AERO_ICE_DRAG_RISE_MAX;

[_liftLoss, _dragRise]
