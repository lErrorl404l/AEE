#include "..\script_component.hpp"

/*
Optics state line.

One grep of "optics state" answers the module's state.  Read only: the
only write is the stateLogStarted flag.  AEE_LOG_INFO on the first call, then
AEE_LOG_DEBUG each tick, so it is readable without the trace switch and cheap
with it off.

The line carries the module readiness, the eye-adaptation core, the shared
post-process flags, the shadow and view-distance state and the live sensor
handle.  Every read has a safe default, so the first line is valid before the
eye, grade and sensor workers have run.
*/

if (!(AEE_TRACE_ON) && {missionNamespace getVariable [QGVAR(stateLogStarted), false]}) exitWith {};

private _isReady = missionNamespace getVariable [QGVAR(isReady), false];
if !(_isReady isEqualType true) then { _isReady = false; };

private _eyeSceneLux = missionNamespace getVariable [QGVAR(eyeSceneLux), 0];
if !(_eyeSceneLux isEqualType 0) then { _eyeSceneLux = 0; };

private _eyeAdaptedLux = missionNamespace getVariable [QGVAR(eyeAdaptedLux), 1];
if !(_eyeAdaptedLux isEqualType 0) then { _eyeAdaptedLux = 1; };

private _eyeAperture = missionNamespace getVariable [QGVAR(eyeAperture), 1];
if !(_eyeAperture isEqualType 0) then { _eyeAperture = 1; };

private _eyeMesopic = missionNamespace getVariable [QGVAR(eyeMesopic), 1];
if !(_eyeMesopic isEqualType 0) then { _eyeMesopic = 1; };

private _chromaActive = missionNamespace getVariable [QGVAR(chromaActive), false];
if !(_chromaActive isEqualType true) then { _chromaActive = false; };

private _blurActive = missionNamespace getVariable [QGVAR(blurActive), false];
if !(_blurActive isEqualType true) then { _blurActive = false; };

private _ccActive = missionNamespace getVariable [QGVAR(ccActive), false];
if !(_ccActive isEqualType true) then { _ccActive = false; };

private _shadowScene = missionNamespace getVariable [QGVAR(shadowScene), "OUTSIDE"];
if !(_shadowScene isEqualType "") then { _shadowScene = "OUTSIDE"; };

private _viewDistanceTarget = missionNamespace getVariable [QGVAR(viewDistanceTarget), 0];
if !(_viewDistanceTarget isEqualType 0) then { _viewDistanceTarget = 0; };

private _sensorPFH = missionNamespace getVariable [QGVAR(sensorPFH), -1];
if !(_sensorPFH isEqualType 0) then { _sensorPFH = -1; };

private _logMsg = format [
    "optics state | ready=%1 | eye=scene:%2 adapted:%3 aperture:%4 mesopic:%5 | pp=chroma:%6 blur:%7 cc:%8 | view=shadow:%9 target:%10m | sensor=%11",
    _isReady,
    round (_eyeSceneLux * 100) / 100, round (_eyeAdaptedLux * 100) / 100,
    round (_eyeAperture * 100) / 100, round (_eyeMesopic * 100) / 100,
    _chromaActive, _blurActive, _ccActive,
    _shadowScene, round (_viewDistanceTarget * 100) / 100, _sensorPFH
];

if (missionNamespace getVariable [QGVAR(stateLogStarted), false]) then {
    AEE_LOG_DEBUG(_logMsg);
} else {
    missionNamespace setVariable [QGVAR(stateLogStarted), true];
    AEE_LOG_INFO(_logMsg);
};
