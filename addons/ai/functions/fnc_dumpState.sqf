#include "..\script_component.hpp"

/*
AI state line.

One grep of "ai state" answers the module's state.  Read only: the
only write is the stateLogStarted flag.  AEE_LOG_INFO on the first call, then
AEE_LOG_DEBUG each tick, so it is readable without the trace switch and cheap
with it off.

The line carries the agent registry size, the disturbance field size, the last
broadcast time, the live tick handle and the forced-decision hook.  Every read
has a safe default, so the first line is valid before any agent has registered.
*/

if (!(AEE_TRACE_ON) && {missionNamespace getVariable [QGVAR(stateLogStarted), false]}) exitWith {};

private _agents = missionNamespace getVariable [QGVAR(agents), []];
if !(_agents isEqualType []) then { _agents = []; };

private _field = missionNamespace getVariable [QGVAR(disturbance), []];
if !(_field isEqualType []) then { _field = []; };

private _lastReport = missionNamespace getVariable [QGVAR(lastReport), -1e9];
if !(_lastReport isEqualType 0) then { _lastReport = -1e9; };

private _aiPFH = missionNamespace getVariable [QGVAR(aiPFH), -1];
if !(_aiPFH isEqualType 0) then { _aiPFH = -1; };

private _forceDecide = missionNamespace getVariable ["aee_ai_forceDecide", -1];
if !(_forceDecide isEqualType 0) then { _forceDecide = -1; };

private _routePlan = missionNamespace getVariable [QGVAR(routePlan), []];
if !(_routePlan isEqualType []) then { _routePlan = []; };

private _logMsg = format [
    "ai state | agents=%1 field=%2 lastReport=%3 pfh=%4 forceDecide=%5 routePlan=%6",
    count _agents, count _field, round (_lastReport * 100) / 100, _aiPFH,
    round _forceDecide, count _routePlan
];

if (missionNamespace getVariable [QGVAR(stateLogStarted), false]) then {
    AEE_LOG_DEBUG(_logMsg);
} else {
    missionNamespace setVariable [QGVAR(stateLogStarted), true];
    AEE_LOG_INFO(_logMsg);
};
