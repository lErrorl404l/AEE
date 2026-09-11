#include "..\script_component.hpp"

/*
Author: AEE
Description: Computes HF ionospheric absorption from the Kp geomagnetic index and the solar flare state published by fnc_calculateSpaceWeather.
Arguments: None
Return Value: NUMBER: absorption 0..1
Example: [] call aee_radio_fnc_calculateIonosphericAbsorption
Public: No
*/

private _kp = missionNamespace getVariable [QEGVAR(environmental,kpIndex), 0];
private _flareActive = missionNamespace getVariable [QEGVAR(environmental,solarFlareActive), false];
private _flareValue = missionNamespace getVariable [QEGVAR(environmental,spaceWeatherFlareValue), 0];

private _absorption = 0.5 * _kp;
if (_flareActive) then {
    _absorption = _absorption + _flareValue;
};
_absorption = _absorption max 0 min 1;

missionNamespace setVariable [QEGVAR(core,ionosphericAbsorption), _absorption];

_absorption
