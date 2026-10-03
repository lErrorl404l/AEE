#include "..\..\script_component.hpp"
/*
 * Fusion outline on/off switch (issue #204).
 *
 * The display class is GVAR(fusionOutline) in addons/thermal/RscTitles.hpp.
 * cutRsc raises the display once; the RscTitles onLoad stores it in
 * uiNamespace as GVAR(outlineDisplay), where FUNC(outlineCanvas) finds it.
 * Toggle is idempotent: a call that matches the current state does nothing.
 *
 * Params:
 *   0: _on (BOOL, default false).
 *
 * Returns: nothing.
 */
params [["_on", false, [true]]];

if (!hasInterface) exitWith {};

private _layer = ["aee_thermal_fusion_outline"] call BIS_fnc_rscLayer;
private _wasOn = missionNamespace getVariable [QGVAR(outlineOn), false];
if !(_wasOn isEqualType true) then { _wasOn = false; };

if (_on) then {
    if (_wasOn) exitWith {};
    _layer cutRsc [QGVAR(fusionOutline), "PLAIN", 0, false];
    missionNamespace setVariable [QGVAR(outlineOn), true];
    private _logMsg = "fusion outline: display raised";
    AEE_LOG_INFO(_logMsg);
} else {
    if (!_wasOn) exitWith {};
    ["clear"] call FUNC(outlineCanvas);
    _layer cutText ["", "PLAIN"];
    missionNamespace setVariable [QGVAR(outlineOn), false];
    private _logMsg = "fusion outline: display cleared";
    AEE_LOG_INFO(_logMsg);
};
