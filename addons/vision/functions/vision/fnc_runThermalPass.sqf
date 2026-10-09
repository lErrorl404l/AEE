#include "..\..\script_component.hpp"
#include "\z\aee\addons\lib\script_debug.hpp"

/*
The per-tick thermal sensor pass.

Shared by the two host channels: the engine thermal channel (Vanilla TI,
currentVisionMode 2) and the day channel (DTV, currentVisionMode 0 with the
vehicle's native TI disabled).  The AGC, the solver and the paint are
identical on both hosts.  The only host difference is the ppEffectForceInNVG
flag, which fnc_applyThermalVision owns.

This body was previously inline in addons/optics/XEH_postInit.sqf.  It was
extracted so the DTV host driver (fnc_dtvHostTick) can run the same pass
without duplicating the call order.
*/

// Thermal optics are parfocal: LWIR wavelength is ~10x visible, so the depth
// of field is so deep that real FLIR sights need NO focus mechanism (fixed at
// the factory).  Kill the NVG DoF effect so its last focus value (e.g.
// PVS-31's 20 m ring) does not leak into the thermal view as a fixed focus
// blur.  The NVG objective-focus handle belongs to nightvision.  Ask that
// addon to release it rather than destroying another module's handle from
// here, so ownership stays with the owner.
BEGIN_COUNTER(teardownNvgDoF);
[] call EFUNC(nightvision,teardownNvgDoF);
END_COUNTER(teardownNvgDoF);

// Scene-adaptive AGC (issue #196): compute the scene's radiance window from
// the physics state BEFORE the per-selection passes read it.  A real FLIR
// re-evaluates its gain continuously from the scene histogram.
BEGIN_COUNTER(updateThermalAGC);
[] call EFUNC(thermal,updateThermalAGC);
END_COUNTER(updateThermalAGC);
BEGIN_COUNTER(applyThermalVision);
[] call EFUNC(thermal_display,applyThermalVision);
END_COUNTER(applyThermalVision);
BEGIN_COUNTER(applyEngineThermal);
[] call EFUNC(thermal,applyEngineThermal);
END_COUNTER(applyEngineThermal);
BEGIN_COUNTER(applyWeaponBarrelHeat);
[] call EFUNC(thermal,applyWeaponBarrelHeat);
END_COUNTER(applyWeaponBarrelHeat);
BEGIN_COUNTER(applySecondSun);
["TICK"] call EFUNC(thermal,applySecondSun);
END_COUNTER(applySecondSun);
BEGIN_COUNTER(applyClothingThermal);
["TICK"] call EFUNC(thermal,applyClothingThermal);
END_COUNTER(applyClothingThermal);
BEGIN_COUNTER(applyBuildingThermal);
["TICK"] call EFUNC(thermal,applyBuildingThermal);
END_COUNTER(applyBuildingThermal);
// Contact conduction: heat exchange between the operator and what they touch
// (vehicle interior, prone ground).  Runs after the object solves so both
// sides have temperatures.
BEGIN_COUNTER(applyContactConduction);
[] call EFUNC(thermal,applyContactConduction);
END_COUNTER(applyContactConduction);
// Radiative exchange (issue #204): a hot object heats the objects around it
// (a hot barrel heats the weapon from inside out, a burning wreck heats
// everything nearby) - Stefan-Boltzmann view-factor transfer.
BEGIN_COUNTER(applyRadiativeExchange);
[] call EFUNC(thermal,applyRadiativeExchange);
END_COUNTER(applyRadiativeExchange);
// Exhaust / emission heat (issue #204): a firing muzzle or running engine
// expels hot gas that warms the ground and air around it (muzzle blast over a
// prone shooter's floor, jet afterburner heating the tarmac).
BEGIN_COUNTER(applyExhaustHeat);
[] call EFUNC(thermal,applyExhaustHeat);
END_COUNTER(applyExhaustHeat);
