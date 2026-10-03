#include "..\..\script_component.hpp"
/*
 * Fusion HUD glass placement (issue #204).
 *
 * Positions the tinted glass panel at the centre of the screen and paints it
 * the fixed fusion colour.  Ported from workshop 3810296503 whale_ecoti_llll
 * functions/fn_boxOnLoad.sqf, which ran from the display's onLoad.  aee stores
 * the display in the config onLoad (the same store-only pattern the fusion
 * outline uses) and calls this from FUNC(hudTapeBoot) once the handle is
 * available, so the glass is placed whether the display is created on the cut
 * frame or the next one.
 *
 * The box is a square whose side is FUSION_HUD_BOX_FRACTION of the safe-zone
 * height, centred: UI x and y units are the same length, so equal w and h draw
 * a square (source fn_boxOnLoad.sqf).
 *
 * Params:
 *   0: _display (DISPLAY, default displayNull).
 *
 * Returns: nothing.
 */
params [["_display", displayNull, [displayNull]]];
if (isNull _display) exitWith {};

uiNamespace setVariable [QGVAR(fusionHudDisplay), _display];

private _frac = FUSION_HUD_BOX_FRACTION;
private _w = _frac * safeZoneH;
private _h = _frac * safeZoneH;
private _x = safeZoneX + safeZoneW / 2 - _w / 2;
private _y = safeZoneY + safeZoneH / 2 - _h / 2;

private _tint = _display displayCtrl 910001;
if (isNull _tint) exitWith {};

_tint ctrlSetPosition [_x, _y, _w, _h];
private _col = FUSION_HUD_GLASS_COLOR;
_tint ctrlSetBackgroundColor _col;
_tint ctrlCommit 0;

missionNamespace setVariable [QGVAR(hudTapeGlassReady), true];
