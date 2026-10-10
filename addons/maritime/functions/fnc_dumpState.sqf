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
private _waterTypeName = missionNamespace getVariable [QGVAR(waterTypeName), ""];
if !(_waterTypeName isEqualType "") then { _waterTypeName = ""; };
private _underwaterKd = missionNamespace getVariable [QGVAR(underwaterKd), [0, 0, 0]];
if !(_underwaterKd isEqualType []) then { _underwaterKd = [0, 0, 0]; };
private _underwaterDepth = missionNamespace getVariable [QGVAR(underwaterDepth), 0];
if !(_underwaterDepth isEqualType 0) then { _underwaterDepth = 0; };
private _underwaterTrans = missionNamespace getVariable [QGVAR(underwaterTrans), [1, 1, 1]];
if !(_underwaterTrans isEqualType []) then { _underwaterTrans = [1, 1, 1]; };
private _snellCritical = missionNamespace getVariable [QGVAR(snellCritical), 0];
if !(_snellCritical isEqualType 0) then { _snellCritical = 0; };
private _snellCone = missionNamespace getVariable [QGVAR(snellCone), 0];
if !(_snellCone isEqualType 0) then { _snellCone = 0; };
private _biolumVisible = missionNamespace getVariable [QGVAR(biolumVisible), false];
if !(_biolumVisible isEqualType false) then { _biolumVisible = false; };
private _biolumIntensity = missionNamespace getVariable [QGVAR(biolumIntensity), 0];
if !(_biolumIntensity isEqualType 0) then { _biolumIntensity = 0; };
private _thermoclineDepth = missionNamespace getVariable [QGVAR(thermoclineDepth_m), 0];
if !(_thermoclineDepth isEqualType 0) then { _thermoclineDepth = 0; };
private _internalWaveSpeed = missionNamespace getVariable [QGVAR(internalWaveSpeed_ms), 0];
if !(_internalWaveSpeed isEqualType 0) then { _internalWaveSpeed = 0; };
private _internalWaveAmplitude = missionNamespace getVariable [QGVAR(internalWaveAmplitude_m), 0];
if !(_internalWaveAmplitude isEqualType 0) then { _internalWaveAmplitude = 0; };
private _internalTideActive = missionNamespace getVariable [QGVAR(internalTideActive), false];

private _logMsg = format [
    "maritime state | sea=beaufort=%1 state=%2 desc=%3 wave=%4 sst=%5 | compass=dev=%6 anomaly=%7 | tide=offset=%8 desc=%9 | water=type:%10 z=%11m Kd=[%12,%13,%14] T=[%15,%16,%17] snell=%18/%19 biolum=%20:%21 | internal=tc=%22 c=%23 eta=%24 active=%25",
    _beaufort, round (_seaStateCurrent * 100) / 100, _seaStateDescription, round (_waveHeight * 100) / 100,
    round (_seaSurfaceTemperature * 100) / 100,
    round (_compassDeviation * 100) / 100, round (_compassAnomalyNT * 100) / 100,
    round (_tideOffset * 100) / 100, _tideDescription,
    _waterTypeName, round (_underwaterDepth * 100) / 100,
    round ((_underwaterKd select 0) * 1000) / 1000,
    round ((_underwaterKd select 1) * 1000) / 1000,
    round ((_underwaterKd select 2) * 1000) / 1000,
    round ((_underwaterTrans select 0) * 1000) / 1000,
    round ((_underwaterTrans select 1) * 1000) / 1000,
    round ((_underwaterTrans select 2) * 1000) / 1000,
    round (_snellCritical * 10) / 10, round (_snellCone * 10) / 10,
    _biolumVisible, round (_biolumIntensity * 100) / 100,
    round (_thermoclineDepth * 100) / 100, round (_internalWaveSpeed * 100) / 100,
    round (_internalWaveAmplitude * 100) / 100, _internalTideActive
];

if (missionNamespace getVariable [QGVAR(stateLogStarted), false]) then {
    AEE_LOG_DEBUG(_logMsg);
} else {
    missionNamespace setVariable [QGVAR(stateLogStarted), true];
    AEE_LOG_INFO(_logMsg);
};
