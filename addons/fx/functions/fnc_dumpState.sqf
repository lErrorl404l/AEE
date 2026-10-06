#include "..\script_component.hpp"

/*
Fx state line.

One grep of "fx state" answers the module's state.  Read only: the only write
is the stateLogStarted flag.  AEE_LOG_INFO on the first call, then
AEE_LOG_DEBUG each tick, so it is readable without the trace switch and cheap
with it off.
*/

if (!(AEE_TRACE_ON) && {missionNamespace getVariable [QGVAR(stateLogStarted), false]}) exitWith {};

private _particles = missionNamespace getVariable [QGVAR(particleSources), []];
if !(_particles isEqualType []) then { _particles = []; };
private _exhaust = missionNamespace getVariable [QGVAR(exhaustSources), []];
if !(_exhaust isEqualType []) then { _exhaust = []; };
private _traces = missionNamespace getVariable [QGVAR(supersonicTrace), []];
if !(_traces isEqualType []) then { _traces = []; };
private _injuries = missionNamespace getVariable [QGVAR(blastInjury), []];
if !(_injuries isEqualType []) then { _injuries = []; };
private _breath = missionNamespace getVariable [QGVAR(breathCondensation), objNull];
if !(_breath isEqualType objNull) then { _breath = objNull; };
private _drops = missionNamespace getVariable [QGVAR(rainSurfaceDrops), objNull];
if !(_drops isEqualType objNull) then { _drops = objNull; };
private _overpressure = missionNamespace getVariable [QGVAR(blastOverpressureKpa), 0];
if !(_overpressure isEqualType 0) then { _overpressure = 0; };
private _refraction = missionNamespace getVariable [QGVAR(exhaustRefraction), 0];
if !(_refraction isEqualType 0) then { _refraction = 0; };
private _dustIntensity = missionNamespace getVariable [QGVAR(vehicleDustIntensity), 1.0];
if !(_dustIntensity isEqualType 0) then { _dustIntensity = 1.0; };
private _atmoDust = missionNamespace getVariable [QGVAR(atmosphericDustIntensity), 0.08];
if !(_atmoDust isEqualType 0) then { _atmoDust = 0.08; };
private _weatherAlpha = missionNamespace getVariable [QGVAR(weatherAlphaEnabled), true];
if !(_weatherAlpha isEqualType true) then { _weatherAlpha = true; };
private _heatHaze = missionNamespace getVariable [QGVAR(heatHazeEnabled), true];
if !(_heatHaze isEqualType true) then { _heatHaze = true; };

private _logMsg = format [
    "fx state | particles=%1 exhaust=%2 traces=%3 blastInj=%4 breath=%5 drops=%6 overpressure=%7 refraction=%8 dust=%9 atmoDust=%10 weatherAlpha=%11 heatHaze=%12",
    count _particles, count _exhaust, count _traces, count _injuries,
    !isNull _breath, !isNull _drops, round (_overpressure * 100) / 100,
    round (_refraction * 100) / 100, round (_dustIntensity * 100) / 100,
    round (_atmoDust * 100) / 100, _weatherAlpha, _heatHaze
];

if (missionNamespace getVariable [QGVAR(stateLogStarted), false]) then {
    AEE_LOG_DEBUG(_logMsg);
} else {
    missionNamespace setVariable [QGVAR(stateLogStarted), true];
    AEE_LOG_INFO(_logMsg);
};
