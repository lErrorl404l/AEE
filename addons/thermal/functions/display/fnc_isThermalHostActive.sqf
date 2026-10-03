#include "..\..\script_component.hpp"

/*
Resolve whether the AEE thermal display owns the current view.

Two host channels exist (AEE Thermal > Display > base channel):

  Vanilla TI (default) - the pipeline runs on the engine's thermal channel,
    currentVisionMode 2.  The result is exactly the pre-existing gate.
  DTV - the pipeline runs on the engine's day channel (currentVisionMode 0)
    while the player is in a vehicle optic and that vehicle's native TI is
    disabled (fnc_updateThermalHost).  This is the A3TI/MKK host: the engine
    renders the day image and AEE paints the heat and layers the sensor
    effects over it.  ppEffectForceInNVG is NOT set on this host - it is an
    NVG-only flag and the DTV frame is not an NVG frame.

The predicate is read live, never cached, so the teardown in
fnc_applyThermalVision can never miss a host change.
*/
params [["_unit", objNull]];
if (!(_unit isEqualType objNull) || {isNull _unit}) exitWith { false };

private _base = missionNamespace getVariable [QGVAR(thermalBaseChannel), 0];
if !(_base isEqualType 0) then { _base = 0; };
if (_base != 1) exitWith { currentVisionMode _unit == 2 };

// DTV: the day channel, in a vehicle optic.  The host manager disables the
// vehicle's native TI, so this view is the only one the day channel shows.
private _veh = vehicle _unit;
(currentVisionMode _unit == 0)
    && (_veh != _unit)
    && (cameraOn == _veh)
    && (cameraView == "GUNNER")
