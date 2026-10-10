#include "..\script_component.hpp"

/*
Ballistics state line.

One grep of "ballistics state" answers the module's state.  Read only: the
only write is the stateLogStarted flag.  AEE_LOG_INFO on the first call,
then AEE_LOG_DEBUG each tick, so it is readable without the trace switch
and cheap with it off.
*/

if (!(AEE_TRACE_ON) && {missionNamespace getVariable [QGVAR(stateLogStarted), false]}) exitWith {};

private _lastShot = missionNamespace getVariable [QGVAR(lastShot), []];
if !(_lastShot isEqualType []) then { _lastShot = []; };
private _lastCartridge = missionNamespace getVariable [QGVAR(lastCartridge), []];
if !(_lastCartridge isEqualType []) then { _lastCartridge = []; };
private _lastRecoil = missionNamespace getVariable [QGVAR(lastRecoil), []];
if !(_lastRecoil isEqualType []) then { _lastRecoil = []; };
private _muzzleVelocityCorrection = missionNamespace getVariable [QGVAR(muzzleVelocityCorrection), 1.0];
if !(_muzzleVelocityCorrection isEqualType 0) then { _muzzleVelocityCorrection = 1.0; };
private _barrelTempC = missionNamespace getVariable [QGVAR(barrelTempC), 0];
if !(_barrelTempC isEqualType 0) then { _barrelTempC = 0; };
private _barrelPOIShiftMrad = missionNamespace getVariable [QGVAR(barrelPOIShiftMrad), 0];
if !(_barrelPOIShiftMrad isEqualType 0) then { _barrelPOIShiftMrad = 0; };
private _barrelColdBore = missionNamespace getVariable [QGVAR(barrelColdBore), 0];
if !(_barrelColdBore isEqualType 0) then { _barrelColdBore = 0; };
private _barrelWearModelled = missionNamespace getVariable [QGVAR(barrelWearModelled), false];
if !(_barrelWearModelled isEqualType false) then { _barrelWearModelled = false; };
private _coriolisDeflection = missionNamespace getVariable [QGVAR(coriolisDeflection_m), 0];
if !(_coriolisDeflection isEqualType 0) then { _coriolisDeflection = 0; };
private _crosswind = missionNamespace getVariable [QGVAR(crosswind), 0];
if !(_crosswind isEqualType 0) then { _crosswind = 0; };
private _downrangeWind = missionNamespace getVariable [QGVAR(downrangeWind), 0];
if !(_downrangeWind isEqualType 0) then { _downrangeWind = 0; };
private _supersonicTrace = missionNamespace getVariable [QGVAR(supersonicTrace), 0];
if !(_supersonicTrace isEqualType 0) then { _supersonicTrace = 0; };
private _seekerState = missionNamespace getVariable [QGVAR(seekerState), 0];
if !(_seekerState isEqualType 0) then { _seekerState = 0; };
private _seekerTracked = missionNamespace getVariable [QGVAR(seekerTracked), false];
if !(_seekerTracked isEqualType false) then { _seekerTracked = false; };
private _seekerRangeM = missionNamespace getVariable [QGVAR(seekerRangeM), 0];
if !(_seekerRangeM isEqualType 0) then { _seekerRangeM = 0; };
private _seekerLosRateRad = missionNamespace getVariable [QGVAR(seekerLosRateRad), 0];
if !(_seekerLosRateRad isEqualType 0) then { _seekerLosRateRad = 0; };
private _seekerCommandMps2 = missionNamespace getVariable [QGVAR(seekerCommandMps2), 0];
if !(_seekerCommandMps2 isEqualType 0) then { _seekerCommandMps2 = 0; };

private _logMsg = format [
    "ballistics state | lastShot=%1 cartridge=%2 recoil=%3 | mv=%4 barrel=%5C poi=%6 cold=%7 wear=%8 | coriolis=%9 cross=%10 downrange=%11 trace=%12 | seeker state=%13 tracked=%14 range=%15 losRate=%16 cmd=%17",
    _lastShot, _lastCartridge, _lastRecoil,
    round (_muzzleVelocityCorrection * 100) / 100, round (_barrelTempC * 100) / 100,
    round (_barrelPOIShiftMrad * 100) / 100, _barrelColdBore, _barrelWearModelled,
    round (_coriolisDeflection * 100) / 100, round (_crosswind * 100) / 100,
    round (_downrangeWind * 100) / 100, round (_supersonicTrace * 100) / 100,
    _seekerState, _seekerTracked, round (_seekerRangeM * 100) / 100,
    round (_seekerLosRateRad * 100) / 100, round (_seekerCommandMps2 * 100) / 100
];

if (missionNamespace getVariable [QGVAR(stateLogStarted), false]) then {
    AEE_LOG_DEBUG(_logMsg);
} else {
    missionNamespace setVariable [QGVAR(stateLogStarted), true];
    AEE_LOG_INFO(_logMsg);
};
