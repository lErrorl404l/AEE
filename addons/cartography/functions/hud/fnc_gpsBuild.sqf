#include "..\..\script_component.hpp"
/*
 * MGRS GPS device display show/hide.
 *
 * Raises the GVAR(gps) RscTitles display on the shared HUD layer, or clears
 * it.  Idempotent: a call that matches the current state does nothing.
 * FUNC(gpsUpdate) calls this each tick from the on/off gate.  The engine GPS
 * readout is fixed, so this display is the aee MGRS surface for the device.
 *
 * Params:
 *   0: _on (BOOL, default true) - true shows the display, false hides it.
 *
 * Returns: nothing.
 */
params [["_on", true, [true]]];

if (!hasInterface) exitWith {};

private _layer = ["aee_optics_gps"] call BIS_fnc_rscLayer;
private _wasOn = missionNamespace getVariable [QGVAR(gpsOn), false];
if !(_wasOn isEqualType true) then { _wasOn = false; };

if (_on) then {
    if (_wasOn) exitWith {};
    _layer cutRsc [QGVAR(gps), "PLAIN", -1, false];
    missionNamespace setVariable [QGVAR(gpsOn), true];
    AEE_LOG_DEBUG("MGRS GPS: display raised");
} else {
    if (!_wasOn) exitWith {};
    _layer cutText ["", "PLAIN"];
    missionNamespace setVariable [QGVAR(gpsOn), false];
    AEE_LOG_DEBUG("MGRS GPS: display cleared");
};
