#include "..\..\script_component.hpp"
/*
 * ECOTI environment HUD show/hide.
 *
 * Raises the GVAR(hud) RscTitles display on the shared HUD layer, or clears
 * it.  Idempotent: a call that matches the current state does nothing.
 * FUNC(hudUpdate) calls this each tick from the on/off gate.
 *
 * Ported from workshop 3759527903 FPANO_ECOTI/scripts/FPANO_fnc_hud.sqf
 * (the cutRsc / cutText raise and clear).  The source raster icons and the
 * audio cue are not shipped; this HUD is text only.
 *
 * Params:
 *   0: _on (BOOL, default true) - true shows the HUD, false hides it.
 *
 * Returns: nothing.
 */
params [["_on", true, [true]]];

if (!hasInterface) exitWith {};

private _layer = ["aee_optics_hud"] call BIS_fnc_rscLayer;
private _wasOn = missionNamespace getVariable [QGVAR(hudOn), false];
if !(_wasOn isEqualType true) then { _wasOn = false; };

if (_on) then {
    if (_wasOn) exitWith {};
    _layer cutRsc [QGVAR(hud), "PLAIN", -1, false];
    missionNamespace setVariable [QGVAR(hudOn), true];
} else {
    if (!_wasOn) exitWith {};
    _layer cutText ["", "PLAIN"];
    missionNamespace setVariable [QGVAR(hudOn), false];
};
