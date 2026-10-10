#include "..\script_component.hpp"

/*
Atmosphere state line.

One grep of "atmos state" answers the module's state.  Read only: the
only write is the stateLogStarted flag.  AEE_LOG_INFO on the first call,
then AEE_LOG_DEBUG each tick, so it is readable without the trace switch
and cheap with it off.
*/

if (!(AEE_TRACE_ON) && {missionNamespace getVariable [QGVAR(stateLogStarted), false]}) exitWith {};

private _edrValue = missionNamespace getVariable [QGVAR(edrValue), 0];
if !(_edrValue isEqualType 0) then { _edrValue = 0; };
private _turbulenceClass = missionNamespace getVariable [QGVAR(turbulenceClass), ""];
if !(_turbulenceClass isEqualType "") then { _turbulenceClass = ""; };
private _airframeIcing = missionNamespace getVariable [QGVAR(airframeIcing), 0];
if !(_airframeIcing isEqualType 0) then { _airframeIcing = 0; };
private _airframeIcingDetected = missionNamespace getVariable [QGVAR(airframeIcingDetected), false];
if !(_airframeIcingDetected isEqualType false) then { _airframeIcingDetected = false; };
private _cloudDescription = missionNamespace getVariable [QGVAR(currentCloudDescription), ""];
if !(_cloudDescription isEqualType "") then { _cloudDescription = ""; };
private _capeProxy = missionNamespace getVariable [QGVAR(capeProxy), 0];
if !(_capeProxy isEqualType 0) then { _capeProxy = 0; };
private _microburstSeverity = missionNamespace getVariable [QGVAR(microburstSeverity), ""];
if !(_microburstSeverity isEqualType "") then { _microburstSeverity = ""; };
private _microburstTimer = missionNamespace getVariable [QGVAR(microburstTimer), 0];
if !(_microburstTimer isEqualType 0) then { _microburstTimer = 0; };
private _microburstWindSpeed = missionNamespace getVariable [QGVAR(microburstWindSpeed), 0];
if !(_microburstWindSpeed isEqualType 0) then { _microburstWindSpeed = 0; };
private _radiationalFog = missionNamespace getVariable [QGVAR(radiationalFog), 0];
if !(_radiationalFog isEqualType 0) then { _radiationalFog = 0; };
private _localWindActive = missionNamespace getVariable [QGVAR(localWindActive), false];
if !(_localWindActive isEqualType false) then { _localWindActive = false; };
private _mirageType = missionNamespace getVariable [QGVAR(mirageType), "None"];
if !(_mirageType isEqualType "") then { _mirageType = "None"; };
private _haloIntensity = missionNamespace getVariable [QGVAR(haloIntensity), 0];
if !(_haloIntensity isEqualType 0) then { _haloIntensity = 0; };
private _haloActive = missionNamespace getVariable [QGVAR(haloActive), false];
if !(_haloActive isEqualType false) then { _haloActive = false; };
private _halo22Inner = missionNamespace getVariable [QGVAR(halo22InnerDeg), 0];
if !(_halo22Inner isEqualType 0) then { _halo22Inner = 0; };
private _halo22Outer = missionNamespace getVariable [QGVAR(halo22OuterDeg), 0];
if !(_halo22Outer isEqualType 0) then { _halo22Outer = 0; };
private _halo46Inner = missionNamespace getVariable [QGVAR(halo46InnerDeg), 0];
if !(_halo46Inner isEqualType 0) then { _halo46Inner = 0; };
private _halo46Outer = missionNamespace getVariable [QGVAR(halo46OuterDeg), 0];
if !(_halo46Outer isEqualType 0) then { _halo46Outer = 0; };
private _sundogOffset = missionNamespace getVariable [QGVAR(sundogOffsetDeg), 0];
if !(_sundogOffset isEqualType 0) then { _sundogOffset = 0; };
private _sundogActive = missionNamespace getVariable [QGVAR(sundogActive), false];
if !(_sundogActive isEqualType false) then { _sundogActive = false; };

private _logMsg = format [
    "atmos state | turbulence=%1/%2 icing=%3/%4 clouds=%5 cape=%6 | microburst=%7 t=%8 wind=%9 | fog=%10 localWind=%11 mirage=%12 | halo=%13/%14 r22=%15-%16 r46=%17-%18 sundog=%19@%20",
    round (_edrValue * 100) / 100, _turbulenceClass, round (_airframeIcing * 100) / 100, _airframeIcingDetected,
    _cloudDescription, round (_capeProxy * 100) / 100,
    _microburstSeverity, round (_microburstTimer * 100) / 100, round (_microburstWindSpeed * 100) / 100,
    round (_radiationalFog * 100) / 100, _localWindActive, _mirageType,
    round (_haloIntensity * 100) / 100, _haloActive,
    round (_halo22Inner * 100) / 100, round (_halo22Outer * 100) / 100,
    round (_halo46Inner * 100) / 100, round (_halo46Outer * 100) / 100,
    _sundogActive, round (_sundogOffset * 100) / 100
];

if (missionNamespace getVariable [QGVAR(stateLogStarted), false]) then {
    AEE_LOG_DEBUG(_logMsg);
} else {
    missionNamespace setVariable [QGVAR(stateLogStarted), true];
    AEE_LOG_INFO(_logMsg);
};
