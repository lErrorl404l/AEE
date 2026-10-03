#include "..\..\script_component.hpp"
/*
 * Fusion thermal-channel frame display driver (issue #204, Track B ENVG-B).
 *
 * Shows and drives the thin rectangular border that marks the thermal
 * channel's half-angle over the NVG view.  The display class is
 * GVAR(fusionFrame) in addons/thermal/RscTitles.hpp, and the thermal fusion
 * path owns it.  It is a HUD aid and NOT optics: no mask and no tube
 * geometry.
 *
 * The border is drawn at an honest on-screen extent from the resolved
 * half-angle: FUNC(fusionFrameGeometry) returns the half-extent as a
 * fraction of safeZoneH, and the four border bars are positioned from it.
 * The angle is NEVER hardcoded; the caller passes the value
 * FUNC(resolveFusionDevice) resolved for the mounted headset.
 *
 * Headless: a dedicated server has no display, so the function returns after
 * the hasInterface guard.  The operator sees the frame; the P80 probe
 * asserts the geometry kernel and the source contract instead.
 *
 * Params:
 *   0: _active (BOOL)         - true to show/update, false to tear down.
 *   1: _halfAngleDeg (SCALAR) - the resolved thermal channel half-angle.
 *   2: _nvgFieldDeg (SCALAR)  - the resolved NVG device full field.
 *
 * Returns: nothing.
 */
params [
    ["_active", false, [true]],
    ["_halfAngleDeg", 20, [0]],
    ["_nvgFieldDeg", 40, [0]]
];

if (!hasInterface) exitWith {};

private _layer = ["aee_thermal_fusion_frame"] call BIS_fnc_rscLayer;

if (!_active) exitWith {
    _layer cutText ["", "PLAIN"];
    missionNamespace setVariable [QGVAR(fusionFrameDisplayUp), false];
};

private _ratio = [_halfAngleDeg, _nvgFieldDeg] call FUNC(fusionFrameGeometry);

if (!(missionNamespace getVariable [QGVAR(fusionFrameDisplayUp), false])) then {
    _layer cutRsc [QGVAR(fusionFrame), "PLAIN", 1, false];
    missionNamespace setVariable [QGVAR(fusionFrameDisplayUp), true];
};

private _disp = uiNamespace getVariable [QGVAR(fusionFrameDisplay), displayNull];
if (isNull _disp) exitWith {};

private _half = (0.5 * _ratio) * safeZoneH;
private _thick = 0.0025 * safeZoneH;
private _cx = safeZoneX + (safeZoneW / 2);
private _cy = safeZoneY + (safeZoneH / 2);

private _top = _disp displayCtrl 1101;
private _bottom = _disp displayCtrl 1102;
private _left = _disp displayCtrl 1103;
private _right = _disp displayCtrl 1104;

_top ctrlSetPosition [_cx - _half, _cy - _half, 2 * _half, _thick];
_bottom ctrlSetPosition [_cx - _half, (_cy + _half) - _thick, 2 * _half, _thick];
_left ctrlSetPosition [_cx - _half, _cy - _half, _thick, 2 * _half];
_right ctrlSetPosition [(_cx + _half) - _thick, _cy - _half, _thick, 2 * _half];
{
    _x ctrlCommit 0;
} forEach [_top, _bottom, _left, _right];
