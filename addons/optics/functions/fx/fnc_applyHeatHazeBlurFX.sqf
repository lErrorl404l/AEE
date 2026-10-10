#include "..\..\script_component.hpp"

/*
Heat-haze defocus post-process contributor (issue #100).

Stores the heat-haze DynamicBlur intensity in QGVAR(heatHazeBlur) for the
central arbiter fnc_managePostProcess.  It REUSES the existing heat-haze
physics: the mirage intensity (fnc_calculateMirageIntensity) that already
drives the Refract particle and the ChromAberration shimmer.  This is NOT a
second DynamicBlur owner; the arbiter is the single owner, and this function
only contributes a value, exactly as fnc_applySolarGlareFX contributes
QGVAR(glareBlur).

The mirage intensity is 0 unless a hot, arid or dusty surface is in view, so
the blur only engages in the heat-haze regime the mirage already detects.

Gates on EGVAR(core,opticsEnabled).  The scale is UNSOURCED (the engine has no
documented heat-haze defocus constant; the value is a small fraction of the
DynamicBlur range the arbiter already uses).

Args: none.  Returns: nothing.
*/

if (!(missionNamespace getVariable [QEGVAR(core,opticsEnabled), true])) exitWith {};

private _mirage = missionNamespace getVariable [QGVAR(mirageIntensity), 0];
if !(_mirage isEqualType 0) then { _mirage = 0; };

// Store 0 below the gate so the arbiter can fade the blur out.  The scale is a
// small fixed fraction of the DynamicBlur range the arbiter already uses.
missionNamespace setVariable [
    QGVAR(heatHazeBlur),
    if (_mirage > 0.1) then { 0.04 * _mirage } else { 0 }
];
