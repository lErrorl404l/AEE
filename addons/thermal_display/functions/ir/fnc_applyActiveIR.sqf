#include "..\..\script_component.hpp"
/*
Per-tick driver for the active-IR illuminator.

CBA_fnc_addPerFrameHandler calls the handler as [_args, _handle], so the
driver declares no top-level params (a top-level params would validate the
handler array and throw every frame).  It runs the pure gate, starts the light
when the operator qualifies, and stops it when the operator dies, the machine
loses its interface, or the setting is disabled.  The gate fails on a
dedicated server, so the driver never runs there.

Returns: BOOL - true when the illuminator is running.
*/
private _unit = call CBA_fnc_currentUnit;

private _settingOn = missionNamespace getVariable [QEGVAR(thermal,activeIR), false];
private _canRun = [
    _settingOn,
    hasInterface,
    isNull _unit,
    alive _unit
] call FUNC(activeIRGate);

if (!_canRun) exitWith {
    [] call FUNC(stopActiveIR);
    false
};

[_unit] call FUNC(startActiveIR);
true
