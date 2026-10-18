#include "..\..\script_component.hpp"
/*
Heat haze / inferior mirage intensity (0.0-1.0).

A near-horizontal light ray curves with the vertical refractivity gradient;
with N = 77.6 P / T (ITU-R P.453), dN/dz = -(77.6 P / T^2)(dT/dz + 0.0342)
per metre, so the ray curves UPWARD - the inferior mirage, the "wet road" -
once the air cools with height faster than the autoconvective lapse,
-dT/dz > 0.0342 K/m (Lehn 1985, J Opt Soc Am A 2:1385; Young, "An
introduction to mirages", SDSU).  The near-ground gradient is the ground
surface temperature the thermal ground solve publishes
(aee_core_surfaceTemperature) against the screen air temperature, over the
1.5 m eye height.  The intensity is the excess gradient over 10 K/m, the
order of a sun-baked road (surface ~15 K above the air at 1 m), as a 0-1
DISPLAY index for the shimmer effect.

Stored in QGVAR(mirageIntensity) for the visual-effect systems.
*/
params [["_unit", objNull, [objNull]]];
if (isNull _unit) exitWith { 0 };

private _tAir = missionNamespace getVariable [QEGVAR(core,currentTemperature), 15];
if !(_tAir isEqualType 0) then { _tAir = 15; };
private _tSurf = missionNamespace getVariable [QEGVAR(core,surfaceTemperature), _tAir];
if !(_tSurf isEqualType 0) then { _tSurf = _tAir; };

private _lapse = (_tSurf - _tAir) / 1.5;
private _intensity = ((_lapse - 0.0342) / (10 - 0.0342)) max 0 min 1;

missionNamespace setVariable [QGVAR(mirageIntensity), _intensity];
_intensity
