#include "..\..\script_component.hpp"

/*
Heat shimmer post-process: ChromAberration.

Reads QGVAR(vehicleHeatShimmerIntensity) (0–1) produced by
fnc_calculateVehicleHeatShimmer (same addon — the stored variable is
aee_optics_vehicleHeatShimmerIntensity).  Gates on EGVAR(core,opticsEnabled).

Computes and stores the heat shimmer ChromAberration intensity in
QGVAR(shimmerChroma); application is handled by fnc_managePostProcess.
*/

if (!EGVAR(core,opticsEnabled)) exitWith {};

private _shimmer = missionNamespace getVariable [QGVAR(vehicleHeatShimmerIntensity), 0];
if !(_shimmer isEqualType 0) then { _shimmer = 0; };

// Setting = visible shimmer at moderate engine heat; store 0 below gate so the arbiter can fade
private _shimmerScale = missionNamespace getVariable [QGVAR(heatShimmerIntensity), 0.04];
missionNamespace setVariable [QGVAR(shimmerChroma), if (_shimmer > 0.1) then { _shimmerScale * _shimmer } else { 0 }];
