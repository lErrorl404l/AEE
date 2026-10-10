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

// Underwater acoustics (issue #113).
private _soundSpeedSurface = missionNamespace getVariable [QGVAR(soundSpeedSurface), 0];
if !(_soundSpeedSurface isEqualType 0) then { _soundSpeedSurface = 0; };
private _soundChannelAxisDepth = missionNamespace getVariable [QGVAR(soundChannelAxisDepth_m), 0];
if !(_soundChannelAxisDepth isEqualType 0) then { _soundChannelAxisDepth = 0; };
private _soundChannelAxisSpeed = missionNamespace getVariable [QGVAR(soundChannelAxisSpeed), 0];
if !(_soundChannelAxisSpeed isEqualType 0) then { _soundChannelAxisSpeed = 0; };
private _shadowZoneTop = missionNamespace getVariable [QGVAR(shadowZoneTop_m), 0];
if !(_shadowZoneTop isEqualType 0) then { _shadowZoneTop = 0; };
private _shadowZoneBottom = missionNamespace getVariable [QGVAR(shadowZoneBottom_m), 0];
if !(_shadowZoneBottom isEqualType 0) then { _shadowZoneBottom = 0; };
private _absorptionDbPerKm = missionNamespace getVariable [QGVAR(absorptionDbPerKm), 0];
if !(_absorptionDbPerKm isEqualType 0) then { _absorptionDbPerKm = 0; };
private _ambientNoiseDb = missionNamespace getVariable [QGVAR(ambientNoiseDb), 0];
if !(_ambientNoiseDb isEqualType 0) then { _ambientNoiseDb = 0; };

private _logMsg = format [
    "maritime state | sea=beaufort=%1 state=%2 desc=%3 wave=%4 sst=%5 | compass=dev=%6 anomaly=%7 | tide=offset=%8 desc=%9 | acoustics=c=%10 axis=%11@%12 shadow=%13..%14 alpha=%15 NL=%16",
    _beaufort, round (_seaStateCurrent * 100) / 100, _seaStateDescription, round (_waveHeight * 100) / 100,
    round (_seaSurfaceTemperature * 100) / 100,
    round (_compassDeviation * 100) / 100, round (_compassAnomalyNT * 100) / 100,
    round (_tideOffset * 100) / 100, _tideDescription,
    round (_soundSpeedSurface * 10) / 10, round _soundChannelAxisDepth, round (_soundChannelAxisSpeed * 10) / 10,
    round _shadowZoneTop, round _shadowZoneBottom,
    round (_absorptionDbPerKm * 1000) / 1000, round _ambientNoiseDb
];

if (missionNamespace getVariable [QGVAR(stateLogStarted), false]) then {
    AEE_LOG_DEBUG(_logMsg);
} else {
    missionNamespace setVariable [QGVAR(stateLogStarted), true];
    AEE_LOG_INFO(_logMsg);
};
