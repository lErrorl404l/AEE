#include "..\script_component.hpp"

/*
Heat shimmer post-process: ChromAberration.

Reads QEGVAR(core,vehicleHeatShimmerIntensity) (0–1) produced by
fn_calculateVehicleHeatShimmer.  Gates on EGVAR(core,opticsEnabled).

Computes and stores the heat shimmer ChromAberration intensity in
QGVAR(shimmerChroma); application is handled by fnc_managePostProcess.
*/

if (!EGVAR(core,opticsEnabled)) exitWith {};

private _shimmer = missionNamespace getVariable [QGVAR(vehicleHeatShimmerIntensity), 0];

// 0.04 = visible shimmer at moderate engine heat; store 0 below gate so the arbiter can fade
missionNamespace setVariable [QGVAR(shimmerChroma), if (_shimmer > 0.1) then { 0.04 * _shimmer } else { 0 }];
