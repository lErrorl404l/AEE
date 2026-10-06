#include "..\..\script_component.hpp"
/*
Stop the active-IR illuminator and destroy the light it created.

Idempotent: a second call finds no light and returns false.  Called by the
toggle, by the death and respawn handlers, and by the per-tick gate when the
operator leaves, dies or disables the setting.

Returns: BOOL - true when a light was destroyed.
*/
private _light = missionNamespace getVariable [QGVAR(activeIRLight), objNull];
if (isNull _light) exitWith { false };

detach _light;
deleteVehicle _light;
missionNamespace setVariable [QGVAR(activeIRLight), objNull];
true
