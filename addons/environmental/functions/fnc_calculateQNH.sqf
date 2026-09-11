#include "..\script_component.hpp"

/*
Author: AEE
Description: Computes QNH (station pressure corrected to sea level) and pressure altitude using the ISA hydrostatic formula.
Arguments: None
Return Value: NUMBER: QNH in hPa
Example: [] call aee_environmental_fnc_calculateQNH
Public: No
*/

private _P = missionNamespace getVariable [QEGVAR(core,currentPressure), 1013.25];

private _altASL = 0;
private _player = call CBA_fnc_currentUnit;
if (!isNil "_player") then {
    _altASL = (getPosASL _player) select 2;
};

// Hydrostatic correction to sea level (ISA lapse rate 0.0065 K/m)
private _qnh = _P * ((1 - (0.0065 * _altASL / 288.15)) ^ -5.2559);

// Pressure altitude from station pressure
private _pressureAltitude = 44330 * (1 - ((_P / 1013.25) ^ 0.1903));

missionNamespace setVariable [QEGVAR(core,qnh), _qnh];
missionNamespace setVariable [QEGVAR(core,pressureAltitude_m), _pressureAltitude];

_qnh
