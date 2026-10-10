#include "..\..\script_component.hpp"
/*
Start the active-IR illuminator for one operator.

UNSOURCED MECHANISM.  The illuminator is a workshop idea re-implemented as
AEE code.  No mod code, value or texture is copied.  The mechanism is an
engine "#lightreflector" light with setLightIR true, so a real NVG or IR optic
sees it and the unaided eye does not.  The light tuning values below have no
published source; they are named here and marked UNSOURCED in the register
docs/wiki/chapters/sensor-value-audit.md.

Creates the light once, attaches it at the operator's position, and stores it
under GVAR(activeIRLight).  The caller owns the lifecycle:
FUNC(stopActiveIR) destroys it.

Params:
    0: _unit (OBJECT) - the operator.

Returns: OBJECT - the light, or objNull when it did not start.
*/
params [["_unit", objNull, [objNull]]];

private _settingOn = missionNamespace getVariable [QEGVAR(thermal,activeIR), false];
private _canRun = [
    _settingOn,
    hasInterface,
    isNull _unit,
    alive _unit
] call FUNC(activeIRGate);
if (!_canRun) exitWith { objNull };

private _light = missionNamespace getVariable [QGVAR(activeIRLight), objNull];
if (isNull _light) then {
    _light = "#lightreflector" createVehicleLocal [0, 0, 0];
    _light setLightIR true;             // IR only: an IR optic sees it, the eye does not
    _light setLightDayLight true;
    _light setLightAmbient [0.02, 0.02, 0.02];
    _light setLightColor [0.15, 0.15, 0.15];
    _light setLightBrightness 0.25;
    missionNamespace setVariable [QGVAR(activeIRLight), _light];
};

_light attachTo [_unit, [0, 0, 0.1]];
_light
