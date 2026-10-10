#include "..\script_component.hpp"

/*
Nightvision state line.

One grep of "nightvision state" answers the module's state.  Read only: the
only write is the stateLogStarted flag.  AEE_LOG_INFO on the first call, then
AEE_LOG_DEBUG each tick, so it is readable without the trace switch and cheap
with it off.
*/

if (!(AEE_TRACE_ON) && {missionNamespace getVariable [QGVAR(stateLogStarted), false]}) exitWith {};

private _tier = missionNamespace getVariable [QGVAR(nvgTubeTier), "NONE"];
if !(_tier isEqualType "") then { _tier = "NONE"; };
private _displayUp = missionNamespace getVariable [QGVAR(nvgDisplayUp), false];
if !(_displayUp isEqualType false) then { _displayUp = false; };
private _gain = missionNamespace getVariable [QGVAR(nvgGain), 0];
if !(_gain isEqualType 0) then { _gain = 0; };
private _noise = missionNamespace getVariable [QGVAR(nvgNoise), 0];
if !(_noise isEqualType 0) then { _noise = 0; };
private _battery = missionNamespace getVariable [QGVAR(nvgBattery), 1.0];
if !(_battery isEqualType 0) then { _battery = 1.0; };
private _blowout = missionNamespace getVariable [QGVAR(nvgBlowout), 0];
if !(_blowout isEqualType 0) then { _blowout = 0; };
private _gate = missionNamespace getVariable [QGVAR(nvgGateActive), false];
if !(_gate isEqualType false) then { _gate = false; };
private _breathing = missionNamespace getVariable [QGVAR(nvgBreathing), 0];
if !(_breathing isEqualType 0) then { _breathing = 0; };
private _perceived = missionNamespace getVariable [QGVAR(nvgPerceived), 0.65];
if !(_perceived isEqualType 0) then { _perceived = 0.65; };
private _imperfection = missionNamespace getVariable [QGVAR(nvgImperfectionAlpha), 0];
if !(_imperfection isEqualType 0) then { _imperfection = 0; };
private _nightGrain = missionNamespace getVariable [QGVAR(nightGrainActive), false];
if !(_nightGrain isEqualType false) then { _nightGrain = false; };
private _ltmPFH = missionNamespace getVariable [QEGVAR(ltm,ltmPFH), -1];
if !(_ltmPFH isEqualType 0) then { _ltmPFH = -1; };

private _logMsg = format [
    "nightvision state | tier=%1 display=%2 gain=%3 noise=%4 battery=%5 blowout=%6 gate=%7 breathing=%8 perceived=%9 imperfection=%10 nightGrain=%11 ltm=%12",
    _tier, _displayUp, round (_gain * 100) / 100, round (_noise * 100) / 100,
    round (_battery * 100) / 100, round (_blowout * 100) / 100, _gate,
    round (_breathing * 100) / 100, round (_perceived * 100) / 100,
    round (_imperfection * 100) / 100, _nightGrain, _ltmPFH
];

if (missionNamespace getVariable [QGVAR(stateLogStarted), false]) then {
    AEE_LOG_DEBUG(_logMsg);
} else {
    missionNamespace setVariable [QGVAR(stateLogStarted), true];
    AEE_LOG_INFO(_logMsg);
};
