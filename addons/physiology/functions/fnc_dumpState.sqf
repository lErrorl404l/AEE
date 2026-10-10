#include "..\script_component.hpp"

/*
Physiology state line.

One grep of "physiology state" answers the module's state.  Read only: the
only write is the stateLogStarted flag.  AEE_LOG_INFO on the first call, then
AEE_LOG_DEBUG each tick, so it is readable without the trace switch and cheap
with it off.
*/

if (!(AEE_TRACE_ON) && {missionNamespace getVariable [QGVAR(stateLogStarted), false]}) exitWith {};

private _sleepState = missionNamespace getVariable [QGVAR(sleepState), 1];
if !(_sleepState isEqualType 0) then { _sleepState = 1; };
private _gLoad = missionNamespace getVariable [QEGVAR(altitude,gLoad), 0];
if !(_gLoad isEqualType 0) then { _gLoad = 0; };
private _gLocStage = missionNamespace getVariable [QEGVAR(altitude,gLocStage), 0];
if !(_gLocStage isEqualType 0) then { _gLocStage = 0; };
private _fatigue = missionNamespace getVariable [QGVAR(fatigueFactor), 1.0];
if !(_fatigue isEqualType 0) then { _fatigue = 1.0; };
private _sleepiness = missionNamespace getVariable [QGVAR(sleepiness), 0];
if !(_sleepiness isEqualType 0) then { _sleepiness = 0; };
private _wakeH = missionNamespace getVariable [QGVAR(wakefulnessHours), 0];
if !(_wakeH isEqualType 0) then { _wakeH = 0; };
private _acclim = missionNamespace getVariable [QEGVAR(altitude,acclimatizationPercent), 0];
if !(_acclim isEqualType 0) then { _acclim = 0; };
private _dehydration = missionNamespace getVariable [QEGVAR(strain,dehydrationRisk), 0];
if !(_dehydration isEqualType 0) then { _dehydration = 0; };
private _altitude = missionNamespace getVariable [QEGVAR(altitude,altitudeState), createHashMap];
if !(_altitude isEqualType createHashMap) then { _altitude = createHashMap; };
private _oxygen = missionNamespace getVariable [QEGVAR(altitude,oxygenState), createHashMap];
if !(_oxygen isEqualType createHashMap) then { _oxygen = createHashMap; };
private _hypoxia = missionNamespace getVariable [QEGVAR(altitude,hypoxiaExposure), createHashMap];
if !(_hypoxia isEqualType createHashMap) then { _hypoxia = createHashMap; };
private _dives = missionNamespace getVariable [QEGVAR(dive,diveStates), createHashMap];
if !(_dives isEqualType createHashMap) then { _dives = createHashMap; };

private _logMsg = format [
    "physiology state | sleep=%1 g=%2 gloc=%3 fatigue=%4 sleepiness=%5 wakeH=%6 acclim=%7 dehydration=%8 | altitude=%9 oxygen=%10 hypoxia=%11 dive=%12",
    _sleepState, round (_gLoad * 100) / 100, _gLocStage,
    round (_fatigue * 100) / 100, round (_sleepiness * 100) / 100,
    round (_wakeH * 100) / 100, round (_acclim * 100) / 100,
    round (_dehydration * 100) / 100, count _altitude, count _oxygen,
    count _hypoxia, count _dives
];

if (missionNamespace getVariable [QGVAR(stateLogStarted), false]) then {
    AEE_LOG_DEBUG(_logMsg);
} else {
    missionNamespace setVariable [QGVAR(stateLogStarted), true];
    AEE_LOG_INFO(_logMsg);
};
