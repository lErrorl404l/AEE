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

ICING.  FAR 25 Appendix C describes where and how fast ice accretes; the
aerodynamic effect at full severity is the FAA's test figure: ice as rough as
medium or coarse sandpaper on the leading edge and upper surface reduces lift
by as much as 30 % and increases drag by 40 % (AC 135-17).  The combined lift
loss is capped at AERO_LIFT_LOSS_CAP, an engine-safety bound, so the scripted
layer cannot stall the airframe on its own.

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
