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

private _eyeSceneLux = missionNamespace getVariable [QEGVAR(eye,eyeSceneLux), 0];
if !(_eyeSceneLux isEqualType 0) then { _eyeSceneLux = 0; };

private _eyeAdaptedLux = missionNamespace getVariable [QEGVAR(eye,eyeAdaptedLux), 1];
if !(_eyeAdaptedLux isEqualType 0) then { _eyeAdaptedLux = 1; };

private _eyeAperture = missionNamespace getVariable [QEGVAR(eye,eyeAperture), 1];
if !(_eyeAperture isEqualType 0) then { _eyeAperture = 1; };

private _eyeMesopic = missionNamespace getVariable [QEGVAR(eye,eyeMesopic), 1];
if !(_eyeMesopic isEqualType 0) then { _eyeMesopic = 1; };

private _chromaActive = missionNamespace getVariable [QEGVAR(vision,chromaActive), false];
if !(_chromaActive isEqualType true) then { _chromaActive = false; };

private _blurActive = missionNamespace getVariable [QEGVAR(vision,blurActive), false];
if !(_blurActive isEqualType true) then { _blurActive = false; };

private _ccActive = missionNamespace getVariable [QEGVAR(vision,ccActive), false];
if !(_ccActive isEqualType true) then { _ccActive = false; };

private _shadowScene = missionNamespace getVariable [QEGVAR(vision,shadowScene), "OUTSIDE"];
if !(_shadowScene isEqualType "") then { _shadowScene = "OUTSIDE"; };

private _viewDistanceTarget = missionNamespace getVariable [QEGVAR(vision,viewDistanceTarget), 0];
if !(_viewDistanceTarget isEqualType 0) then { _viewDistanceTarget = 0; };

private _sensorPFH = missionNamespace getVariable [QEGVAR(vision,sensorPFH), -1];
if !(_sensorPFH isEqualType 0) then { _sensorPFH = -1; };

private _greenFlashIntensity = missionNamespace getVariable [QGVAR(greenFlashIntensity), 0];
if !(_greenFlashIntensity isEqualType 0) then { _greenFlashIntensity = 0; };
private _greenFlashActive = missionNamespace getVariable [QGVAR(greenFlashActive), false];
if !(_greenFlashActive isEqualType false) then { _greenFlashActive = false; };
private _greenFlashDuration = missionNamespace getVariable [QGVAR(greenFlashDurationS), 0];
if !(_greenFlashDuration isEqualType 0) then { _greenFlashDuration = 0; };

private _logMsg = format [
    "optics state | ready=%1 | eye=scene:%2 adapted:%3 aperture:%4 mesopic:%5 | pp=chroma:%6 blur:%7 cc:%8 | view=shadow:%9 target:%10m | sensor=%11 | greenFlash=%12/%13 %14s",
    _isReady,
    round (_eyeSceneLux * 100) / 100, round (_eyeAdaptedLux * 100) / 100,
    round (_eyeAperture * 100) / 100, round (_eyeMesopic * 100) / 100,
    _chromaActive, _blurActive, _ccActive,
    _shadowScene, round (_viewDistanceTarget * 100) / 100, _sensorPFH,
    round (_greenFlashIntensity * 100) / 100, _greenFlashActive,
    round (_greenFlashDuration * 100) / 100
];

if (missionNamespace getVariable [QGVAR(stateLogStarted), false]) then {
    AEE_LOG_DEBUG(_logMsg);
} else {
    missionNamespace setVariable [QGVAR(stateLogStarted), true];
    AEE_LOG_INFO(_logMsg);
};
