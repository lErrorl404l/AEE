#include "..\script_component.hpp"

/*
Thermal state line.

One grep of "thermal state" answers the module's state.  Read only: the only
write is the stateLogStarted flag.  AEE_LOG_INFO on the first call, then
AEE_LOG_DEBUG each tick, so it is readable without the trace switch and cheap
with it off.
*/

if (!(AEE_TRACE_ON) && {missionNamespace getVariable [QGVAR(stateLogStarted), false]}) exitWith {};

private _active = missionNamespace getVariable [QEGVAR(thermal_display,thermalActive), false];
if !(_active isEqualType false) then { _active = false; };
private _displayMode = missionNamespace getVariable [QGVAR(thermalDisplayMode), 0];
if !(_displayMode isEqualType 0) then { _displayMode = 0; };
private _palette = missionNamespace getVariable [QGVAR(thermalPalette), 0];
if !(_palette isEqualType 0) then { _palette = 0; };
private _polarity = missionNamespace getVariable [QGVAR(thermalPolarity), 0];
if !(_polarity isEqualType 0) then { _polarity = 0; };
private _fusionMode = missionNamespace getVariable [QEGVAR(thermal_display,fusionMode), 0];
if !(_fusionMode isEqualType 0) then { _fusionMode = 0; };
private _outlineOn = missionNamespace getVariable [QEGVAR(thermal_display,outlineOn), false];
if !(_outlineOn isEqualType false) then { _outlineOn = false; };
private _hudTapeOn = missionNamespace getVariable [QEGVAR(thermal_display,hudTapeOn), false];
if !(_hudTapeOn isEqualType false) then { _hudTapeOn = false; };
private _activeIR = missionNamespace getVariable [QGVAR(activeIR), false];
if !(_activeIR isEqualType false) then { _activeIR = false; };
private _agcPinned = missionNamespace getVariable [QGVAR(agcPinned), false];
if !(_agcPinned isEqualType false) then { _agcPinned = false; };
private _bloom = missionNamespace getVariable [QEGVAR(thermal_display,bloom), 0];
if !(_bloom isEqualType 0) then { _bloom = 0; };
private _manualMinC = missionNamespace getVariable [QGVAR(thermalManualMinC), -40];
if !(_manualMinC isEqualType 0) then { _manualMinC = -40; };
private _manualMaxC = missionNamespace getVariable [QGVAR(thermalManualMaxC), 120];
if !(_manualMaxC isEqualType 0) then { _manualMaxC = 120; };

private _logMsg = format [
    "thermal state | active=%1 mode=%2 palette=%3 polarity=%4 fusion=%5 outline=%6 hud=%7 activeIR=%8 agcPinned=%9 bloom=%10 minC=%11 maxC=%12",
    _active, _displayMode, _palette, _polarity, _fusionMode, _outlineOn,
    _hudTapeOn, _activeIR, _agcPinned, round (_bloom * 100) / 100,
    round (_manualMinC * 100) / 100, round (_manualMaxC * 100) / 100
];

if (missionNamespace getVariable [QGVAR(stateLogStarted), false]) then {
    AEE_LOG_DEBUG(_logMsg);
} else {
    missionNamespace setVariable [QGVAR(stateLogStarted), true];
    AEE_LOG_INFO(_logMsg);
};
