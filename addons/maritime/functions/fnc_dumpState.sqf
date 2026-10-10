#include "..\script_component.hpp"

/*
Maritime state line.

One grep of "maritime state" answers the module's state.  Read only: the
only write is the stateLogStarted flag.  AEE_LOG_INFO on the first call,
then AEE_LOG_DEBUG each tick, so it is readable without the trace switch
and cheap with it off.
*/

if (!(AEE_TRACE_ON) && {missionNamespace getVariable [QGVAR(stateLogStarted), false]}) exitWith {};

private _beaufort = missionNamespace getVariable [QEGVAR(core,seaStateBeaufort), 0];
if !(_beaufort isEqualType 0) then { _beaufort = 0; };
private _seaStateCurrent = missionNamespace getVariable [QEGVAR(core,seaStateCurrent), 0];
if !(_seaStateCurrent isEqualType 0) then { _seaStateCurrent = 0; };
private _seaStateDescription = missionNamespace getVariable [QEGVAR(core,seaStateDescription), ""];
if !(_seaStateDescription isEqualType "") then { _seaStateDescription = ""; };
private _waveHeight = missionNamespace getVariable [QGVAR(waveHeight_m), 0];
if !(_waveHeight isEqualType 0) then { _waveHeight = 0; };
private _seaSurfaceTemperature = missionNamespace getVariable [QGVAR(seaSurfaceTemperature), 0];
if !(_seaSurfaceTemperature isEqualType 0) then { _seaSurfaceTemperature = 0; };
private _compassDeviation = missionNamespace getVariable [QEGVAR(magnetism,compassDeviation), 0];
if !(_compassDeviation isEqualType 0) then { _compassDeviation = 0; };
private _compassAnomalyNT = missionNamespace getVariable [QEGVAR(magnetism,compassAnomalyNT), 0];
if !(_compassAnomalyNT isEqualType 0) then { _compassAnomalyNT = 0; };
private _tideOffset = missionNamespace getVariable [QEGVAR(core,currentTideOffset_m), 0];
if !(_tideOffset isEqualType 0) then { _tideOffset = 0; };
private _tideDescription = missionNamespace getVariable [QEGVAR(core,currentTideDescription), ""];
if !(_tideDescription isEqualType "") then { _tideDescription = ""; };

private _logMsg = format [
    "maritime state | sea=beaufort=%1 state=%2 desc=%3 wave=%4 sst=%5 | compass=dev=%6 anomaly=%7 | tide=offset=%8 desc=%9",
    _beaufort, round (_seaStateCurrent * 100) / 100, _seaStateDescription, round (_waveHeight * 100) / 100,
    round (_seaSurfaceTemperature * 100) / 100,
    round (_compassDeviation * 100) / 100, round (_compassAnomalyNT * 100) / 100,
    round (_tideOffset * 100) / 100, _tideDescription
];

if (missionNamespace getVariable [QGVAR(stateLogStarted), false]) then {
    AEE_LOG_DEBUG(_logMsg);
} else {
    missionNamespace setVariable [QGVAR(stateLogStarted), true];
    AEE_LOG_INFO(_logMsg);
};
