#include "..\..\script_component.hpp"

/*
Author: AEE
Description: Computes fog base altitude from the temperature-dewpoint spread using a Magnus approximation for dew point. Returns 9999 when no fog forms.
Arguments: None
Return Value: NUMBER: fog base in metres (9999 = no fog)
Example: [] call aee_weather_fnc_calculateFogBaseAltitude
Public: No
*/

private _T = missionNamespace getVariable [QEGVAR(core,currentTemperature), 15];
private _RH = missionNamespace getVariable [QEGVAR(core,currentHumidity), 50];

// Magnus dew point over water, WMO-No. 8 Annex 4.B coefficients (17.62,
// 243.12); the same pair is Alduchov & Eskridge 1996.  The earlier citation
// "Sonntag 1990" is wrong: Sonntag's water formula is a log-polynomial, not
// this Magnus pair.
private _gamma = (ln (_RH / 100)) + (17.62 * _T / (243.12 + _T));
private _Td = 243.12 * _gamma / (17.62 - _gamma);
private _spread = _T - _Td;

private _fogBase = 9999;
if (_spread < 2.5) then {
    _fogBase = (125 * _spread) max 0;
};

missionNamespace setVariable [QEGVAR(core,fogBase_m), _fogBase];

_fogBase
