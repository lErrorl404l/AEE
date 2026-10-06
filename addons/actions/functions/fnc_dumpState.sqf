#include "..\script_component.hpp"

/*
actions state line.

One grep of "actions state" answers the module's state.  Read only: the only
write is the stateLogStarted flag.  AEE_LOG_INFO on the first call, then
AEE_LOG_DEBUG each tick, so it is readable without the trace switch and cheap
with it off.

The actions module publishes no state of its own.  Its keybinds set the NVG
depth-of-field hooks on the nightvision component, so the line reports those
hooks: the focus mode, the manual ring distance and whether the mode has been
initialised by the tube model.

Nothing here changes state and nothing broadcasts.  Every value carries a
safe default so the first line is valid before a unit has racked the ring.
*/

if (!(AEE_TRACE_ON) && {missionNamespace getVariable [QGVAR(stateLogStarted), false]}) exitWith {};

// 0 = AUTO (the tube-model state machine), 1 = MANUAL (the manual ring).
private _dofMode = missionNamespace getVariable [QEGVAR(nightvision,dofMode), 0];
if !(_dofMode isEqualType 0) then { _dofMode = 0; };

// The manual ring distance in metres, clamped by the keybind to 0.25..300.
private _dofManualDist = missionNamespace getVariable [QEGVAR(nightvision,dofManualDist), 15];
if !(_dofManualDist isEqualType 0) then { _dofManualDist = 15; };

// Set by the tube model once it has published the mode.
private _dofModeSet = missionNamespace getVariable [QEGVAR(nightvision,dofModeSet), false];
if !(_dofModeSet isEqualType false) then { _dofModeSet = false; };

private _logMsg = format [
    "actions state | dofMode=%1 manualDist=%2 modeSet=%3",
    round _dofMode, round (_dofManualDist * 100) / 100, _dofModeSet
];

if (missionNamespace getVariable [QGVAR(stateLogStarted), false]) then {
    AEE_LOG_DEBUG(_logMsg);
} else {
    missionNamespace setVariable [QGVAR(stateLogStarted), true];
    AEE_LOG_INFO(_logMsg);
};
