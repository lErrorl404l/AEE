#include "..\..\script_component.hpp"
/*
 * Fusion HUD viewfinder box (workshop 3810296503 whale_ecoti_llll).
 *
 * The source's box is the ecoti_tint control (config.cpp, idc 910001): a square
 * centred on the screen whose side is the source's boxSize of the safe-zone
 * height (fn_preInit.sqf boxSize 0.40; fn_boxOnLoad.sqf places it at
 * safeZoneX + safeZoneW / 2 - w / 2, and the same for Y).  The source paints
 * it as one translucent fill; a fill warms the green phosphor, so aee draws the
 * same rectangle as its four EDGES in the source's own box colour
 * (config.cpp ecoti_tint colorBackground, FUSION_BOX_COLOR).  The operator
 * keeps the box and the NVG stays green (operator report 2026-10-03).
 *
 * The colour follows FUNC(hudTapeBoot)'s QGVAR(hudTapeBootProfile) index 0, so
 * the box fades with the tape on power-on and power-off.
 *
 * Returns: nothing.
 */
if (!hasInterface) exitWith {};

private _raised = missionNamespace getVariable [QGVAR(hudTapeOn), false];
if !(_raised isEqualType true) then { _raised = false; };
if (!_raised) exitWith {};

private _disp = uiNamespace getVariable [QGVAR(fusionHudDisplay), displayNull];
if (isNull _disp) exitWith {};

private _prof = missionNamespace getVariable [QGVAR(hudTapeBootProfile), [1, 1]];
if !(_prof isEqualType []) then { _prof = [1, 1]; };
private _bootK = if ((count _prof) > 0) then { _prof select 0 } else { 1 };
if !(_bootK isEqualType 0) then { _bootK = 1; };

private _base = FUSION_BOX_COLOR;
private _col = [
    (_base select 0) * _bootK,
    (_base select 1) * _bootK,
    (_base select 2) * _bootK,
    (_base select 3) * _bootK
];

private _bw = FUSION_HUD_BOX_FRACTION * safeZoneH;
private _bh = FUSION_HUD_BOX_FRACTION * safeZoneH;
private _bx = safeZoneX + safeZoneW / 2 - _bw / 2;
private _by = safeZoneY + safeZoneH / 2 - _bh / 2;
private _thick = FUSION_BOX_THICKNESS * safeZoneH;

private _top = _disp displayCtrl 910001;
private _bottom = _disp displayCtrl 910002;
private _left = _disp displayCtrl 910003;
private _right = _disp displayCtrl 910004;

if (!isNull _top) then {
    _top ctrlSetPosition [_bx, _by, _bw, _thick];
    _top ctrlSetBackgroundColor _col;
    _top ctrlCommit 0;
};
if (!isNull _bottom) then {
    _bottom ctrlSetPosition [_bx, _by + _bh - _thick, _bw, _thick];
    _bottom ctrlSetBackgroundColor _col;
    _bottom ctrlCommit 0;
};
if (!isNull _left) then {
    _left ctrlSetPosition [_bx, _by, _thick, _bh];
    _left ctrlSetBackgroundColor _col;
    _left ctrlCommit 0;
};
if (!isNull _right) then {
    _right ctrlSetPosition [_bx + _bw - _thick, _by, _thick, _bh];
    _right ctrlSetBackgroundColor _col;
    _right ctrlCommit 0;
};
