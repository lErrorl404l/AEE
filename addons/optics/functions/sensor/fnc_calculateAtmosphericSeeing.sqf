#include "..\..\script_component.hpp"

/*
Atmospheric seeing index (0.1-1.0) for long-range optics.  Higher is worse
(more shimmer).

The refractive-index structure constant Cn^2 along a sight line 2 m above
the ground is the surface-layer value fnc_calculateTurbulence publishes
(aee_core_opticalCn2: Wyngaard, Izumi & Collins 1971 C_T^2 from the
Monin-Obukhov heat flux and stability, Cn^2 = (79e-6 P / T^2)^2 C_T^2).
The index is a log scale over the range of near-ground optical turbulence,
Cn^2 1e-17 (very weak) to 1e-12 m^-2/3 (very strong) (Andrews & Phillips,
Laser Beam Propagation through Random Media, 2nd ed., s.3.3), mapped onto
the 0.1-1.0 display index the shimmer effect consumes.

Stored in QGVAR(atmosphericSeeing).  Lower = better.
*/

private _cn2 = missionNamespace getVariable [QEGVAR(core,opticalCn2), 1e-15];
if !(_cn2 isEqualType 0) then { _cn2 = 1e-15; };
private _logCn2 = log ((_cn2 max 1e-17) min 1e-12);
private _seeing = 0.1 + 0.9 * ((_logCn2 + 17) / 5);
_seeing = _seeing max 0.1 min 1.0;

missionNamespace setVariable [QGVAR(atmosphericSeeing), _seeing];

_seeing
