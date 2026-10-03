#include "..\..\script_component.hpp"

/*
DTV base-channel host manager (prototype).

When AEE Thermal > Display > base channel is DTV, the engine's native TI
channel is disabled on the player's vehicle and the thermal display runs on
the day (DTV) channel instead - the host channel A3TI and MKK use.  The
pipeline itself (AGC, solver, paint, ppEffects) is unchanged; only the host
channel and the ppEffectForceInNVG flag differ.

This function owns the state transition:
  - disableTIEquipment true on the vehicle while the player is in its optic;
  - restore disableTIEquipment false on exit or vehicle switch;
  - run the thermal sensor ENTER once when the host becomes active and EXIT
    once when it stops.

It returns true while the DTV host is active.  fnc_dtvHostTick calls it each
tick; fnc_dtvHostStop calls it once on shutdown to restore.
*/
params [["_player", call CBA_fnc_currentUnit]];

private _base = missionNamespace getVariable [QEGVAR(thermal,thermalBaseChannel), 0];
if !(_base isEqualType 0) then { _base = 0; };

private _tracked = missionNamespace getVariable [QGVAR(dtvHostVehicle), objNull];
private _active = false;

if ((_base == 1) && {!isNull _player} && {alive _player}) then {
    private _veh = vehicle _player;
    _active = (currentVisionMode _player == 0)
        && (_veh != _player)
        && (cameraOn == _veh)
        && (cameraView == "GUNNER");
    if (_active && (_tracked != _veh)) then {
        if (!isNull _tracked) then { _tracked disableTIEquipment false; };
        missionNamespace setVariable [QGVAR(dtvHostVehicle), _veh];
        _veh disableTIEquipment true;
    };
};

// Restore the native TI of the vehicle we disabled, on exit or switch.
if (!_active && {!isNull _tracked}) then {
    _tracked disableTIEquipment false;
    missionNamespace setVariable [QGVAR(dtvHostVehicle), objNull];
};

// ENTER/EXIT the thermal sensor session once per host change.
private _entered = missionNamespace getVariable [QGVAR(dtvHostEntered), false];
if (_active && {!_entered}) then {
    missionNamespace setVariable [QGVAR(dtvHostEntered), true];
    [] call FUNC(enterThermalSensors);
    AEE_LOG_INFO("DTV thermal host entered");
};
if (!_active && _entered) then {
    missionNamespace setVariable [QGVAR(dtvHostEntered), false];
    [] call FUNC(exitThermalSensors);
    AEE_LOG_INFO("DTV thermal host exited");
};

_active
