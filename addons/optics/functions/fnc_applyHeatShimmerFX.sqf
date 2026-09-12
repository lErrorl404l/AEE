#include "..\script_component.hpp"

/*
Heat shimmer post-process: ChromAberration.

Reads QEGVAR(core,vehicleHeatShimmerIntensity) (0–1) produced by
fn_calculateVehicleHeatShimmer.  Gates on EGVAR(core,opticsEnabled).

When intensity > 0.1, applies subtle chromatic aberration that mimics
refractive distortion near hot engine/exhaust areas.  Fades to zero and
disables the effect when intensity drops below 0.1, using a flag
(QGVAR(shimmerFXActive)) to avoid redundant callbacks.
*/

if (!EGVAR(core,opticsEnabled)) exitWith {};

private _shimmer = missionNamespace getVariable [QGVAR(vehicleHeatShimmerIntensity), 0];
private _active  = missionNamespace getVariable [QGVAR(shimmerFXActive), false];

if (_shimmer > 0.1) then {
    if (!_active) then {
        "ChromAberration" ppEffectEnable true;
        missionNamespace setVariable [QGVAR(shimmerFXActive), true];
    };

    // 0.04 = visible shimmer at moderate engine heat
    "ChromAberration" ppEffectAdjust [0.04 * _shimmer, 0.04 * _shimmer, true];
    "ChromAberration" ppEffectCommit 2;
} else {
    if (_active) then {
        "ChromAberration" ppEffectAdjust [0, 0, true];
        "ChromAberration" ppEffectCommit 1;

        [{
            "ChromAberration" ppEffectEnable false;
        }, [], 1.5] call CBA_fnc_waitAndExecute;

        missionNamespace setVariable [QGVAR(shimmerFXActive), false];
    };
};
