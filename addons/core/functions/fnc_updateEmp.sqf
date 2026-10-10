#include "..\script_component.hpp"

/*
Nuclear EMP event tick (issue #9).

The driver for the EMP model.  It runs once per environment tick, after the
burst is set by fnc_triggerEmp.  It reads the burst state, computes the free
field at the player position with the pure kernels and publishes the
per-system degradation factors the radio and optics modules consume.

Impulse capture: the E1 field is a nanosecond-scale impulse (IEC 61000-2-9),
so the field is sampled ONCE on the first tick after the burst and the device
effect then recovers with its own time constant.  The tick does not re-sample
the field every second, which would be physically wrong.

Hardening (issue #9): the radio antenna front end and the optical sensor
aperture are treated as unhardened (0 dB); the coupled field is the free field
reduced by the barrier, per fnc_calculateEmpCoupling.

Device thresholds (issue #9):
  comms (handheld radio)  upset 2 kV/m, damage 10 kV/m  -> the radio factor
  optoelectronics         upset 1 kV/m, damage  5 kV/m  -> the optics factor

The event clears once both systems have recovered.

Arguments:
  0: posASL (ARRAY) - the position to evaluate the field at (the player)

Return Value: NUMBER - the radio degradation factor (1.0 when intact)
Example: [[0,0,0]] call aee_core_fnc_updateEmp
Public: No
*/

params [["_posASL", [0, 0, 0], [[]]]];

if (!GVAR(empEnabled)) exitWith { 1 };

private _active = missionNamespace getVariable [QGVAR(empActive), false];
if (!_active) exitWith { 1 };

private _burstPos = missionNamespace getVariable [QGVAR(empBurstPos), [0, 0, 0]];
private _type = missionNamespace getVariable [QGVAR(empBurstType), "hemp"];
private _alt = missionNamespace getVariable [QGVAR(empBurstAltM), 400000];
private _peak = missionNamespace getVariable [QGVAR(empPeakVpm), 50000];
private _start = missionNamespace getVariable [QGVAR(empStartTime), 0];
private _elapsed = CBA_missionTime - _start;

private _dx = (_posASL select 0) - (_burstPos select 0);
private _dy = (_posASL select 1) - (_burstPos select 1);
private _dist = sqrt ((_dx * _dx) + (_dy * _dy));

private _captured = missionNamespace getVariable [QGVAR(empCaptured), false];
private _free = 0;
private _radioCoupled = missionNamespace getVariable [QGVAR(empRadioCoupledVpm), 0];
private _opticsCoupled = missionNamespace getVariable [QGVAR(empOpticsCoupledVpm), 0];
private _radioF0 = missionNamespace getVariable [QGVAR(empRadioF0), 1];
private _opticsF0 = missionNamespace getVariable [QGVAR(empOpticsF0), 1];
private _radioTau = missionNamespace getVariable [QGVAR(empRadioTauS), 1];
private _opticsTau = missionNamespace getVariable [QGVAR(empOpticsTauS), 1];

if (!_captured) then {
    _free = [_type, _dist, _alt, _peak] call FUNC(calculateEmpField);
    _radioCoupled = [_free, 0] call FUNC(calculateEmpCoupling);
    _opticsCoupled = [_free, 0] call FUNC(calculateEmpCoupling);
    _radioF0 = [_radioCoupled, 10000] call FUNC(calculateEmpDegradation);
    _opticsF0 = [_opticsCoupled, 5000] call FUNC(calculateEmpDegradation);
    _radioTau = [_radioCoupled, 10000] call FUNC(calculateEmpRecovery);
    _opticsTau = [_opticsCoupled, 5000] call FUNC(calculateEmpRecovery);

    missionNamespace setVariable [QGVAR(empFreeFieldVpm), _free];
    missionNamespace setVariable [QGVAR(empRadioCoupledVpm), _radioCoupled];
    missionNamespace setVariable [QGVAR(empOpticsCoupledVpm), _opticsCoupled];
    missionNamespace setVariable [QGVAR(empRadioF0), _radioF0];
    missionNamespace setVariable [QGVAR(empOpticsF0), _opticsF0];
    missionNamespace setVariable [QGVAR(empRadioTauS), _radioTau];
    missionNamespace setVariable [QGVAR(empOpticsTauS), _opticsTau];
    missionNamespace setVariable [QGVAR(empCaptured), true];

    private _logMsg = format [
        "EMP captured (%1) at %2 m: free %3 V/m, radio coupled %4 V/m, radio tau %5 s",
        _type, round _dist, round _free, round _radioCoupled, round _radioTau
    ];
    AEE_LOG_INFO(_logMsg);
};

private _radioFactor = [_radioF0, _elapsed, _radioTau] call FUNC(calculateEmpRecoveredFactor);
private _opticsFactor = [_opticsF0, _elapsed, _opticsTau] call FUNC(calculateEmpRecoveredFactor);

missionNamespace setVariable [QGVAR(empRadioFactor), _radioFactor];
missionNamespace setVariable [QGVAR(empOpticsFactor), _opticsFactor];

// The event ends when both systems have recovered.
if ((_radioFactor > 0.999) && (_opticsFactor > 0.999)) then {
    missionNamespace setVariable [QGVAR(empActive), false];
};

_radioFactor
