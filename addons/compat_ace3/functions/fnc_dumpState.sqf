#include "..\script_component.hpp"

/*
compat_ace3 state line.

One grep of "compat_ace3 state" answers the module's state.  Read only: the
only write is the stateLogStarted flag.  AEE_LOG_INFO on the first call, then
AEE_LOG_DEBUG each tick, so it is readable without the trace switch and cheap
with it off.

The line carries the medical vitals mapping (the heat-stress and heat-stroke
flags and the burn exposure counter), the ACE weather bridge values it
publishes, and the resolver counts registered into the physiology library.
Every value carries a safe default so the first line is valid before the
medical tick or the Kestrel bridge has run.

Nothing here changes state and nothing broadcasts.
*/

if (!(AEE_TRACE_ON) && {missionNamespace getVariable [QGVAR(stateLogStarted), false]}) exitWith {};

// The vitals mapping state, published by fnc_integrateMedical.
private _heatStress = missionNamespace getVariable [QGVAR(heatStressAdjustmentActive), false];
if !(_heatStress isEqualType false) then { _heatStress = false; };
private _heatStroke = missionNamespace getVariable [QGVAR(heatStrokeActive), false];
if !(_heatStroke isEqualType false) then { _heatStroke = false; };
private _burnTicks = missionNamespace getVariable [QGVAR(burnExposureTicks), 0];
if !(_burnTicks isEqualType 0) then { _burnTicks = 0; };

// The ACE weather bridge values, published by fnc_integrateKestrel.
private _aceTemp = missionNamespace getVariable ["ace_weather_currentTemperature", 15];
if !(_aceTemp isEqualType 0) then { _aceTemp = 15; };
private _aceWBGT = missionNamespace getVariable ["ace_weather_currentWBGT", 15];
if !(_aceWBGT isEqualType 0) then { _aceWBGT = 15; };

// The resolver hooks this module registered into the physiology library.
private _massResolvers = missionNamespace getVariable ["aee_physiology_massResolvers", []];
if !(_massResolvers isEqualType []) then { _massResolvers = []; };
private _categoryResolvers = missionNamespace getVariable ["aee_physiology_categoryResolvers", []];
if !(_categoryResolvers isEqualType []) then { _categoryResolvers = []; };

private _logMsg = format [
    "compat_ace3 state | heatStress=%1 heatStroke=%2 burnTicks=%3 | aceTemp=%4 aceWBGT=%5 | resolvers=mass:%6 category:%7",
    _heatStress, _heatStroke, round _burnTicks,
    round (_aceTemp * 100) / 100, round (_aceWBGT * 100) / 100,
    count _massResolvers, count _categoryResolvers
];

if (missionNamespace getVariable [QGVAR(stateLogStarted), false]) then {
    AEE_LOG_DEBUG(_logMsg);
} else {
    missionNamespace setVariable [QGVAR(stateLogStarted), true];
    AEE_LOG_INFO(_logMsg);
};
