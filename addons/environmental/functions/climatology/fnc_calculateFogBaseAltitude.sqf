#include "..\..\script_component.hpp"

/*
Author: AEE
Description: Computes fog base altitude from the temperature-dewpoint spread using a Magnus approximation for dew point. Returns 9999 when no fog forms.
Arguments: None
Return Value: NUMBER: fog base in metres (9999 = no fog)
Example: [] call aee_environmental_fnc_calculateFogBaseAltitude
Public: No
*/

private _T = missionNamespace getVariable [QEGVAR(core,currentTemperature), 15];
private _RH = missionNamespace getVariable [QEGVAR(core,currentHumidity), 50];

// Magnus dew point (Sonntag 1990, over water)
private _gamma = (ln (_RH / 100)) + (17.62 * _T / (243.12 + _T));
private _Td = 243.12 * _gamma / (17.62 - _gamma);
private _spread = _T - _Td;

private _fogBase = 9999;
if (_spread < 2.5) then {
    _fogBase = (125 * _spread) max 0;
};

missionNamespace setVariable [QEGVAR(core,fogBase_m), _fogBase];

_fogBase
