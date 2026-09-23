#include "..\..\script_component.hpp"

/*
Freezing rain / icing detection.

Conditions for freezing rain:
  • Surface air temperature < 0 °C
  • Precipitation (rain > 0)
  • Warm layer above suspected — assumed when overcast > 0.6 and altitude < 500 m

Sets GVAR(currentFreezingRain)  — bool
Sets GVAR(currentIcingSeverity) — float 0–1
*/

private _T_C = missionNamespace getVariable [QEGVAR(core,currentTemperature), 15];
private _rain = rain;

if (isNil "_T_C")  exitWith {};
if (isNil "_rain") exitWith {};

private _isFreezing = false;
private _severity   = 0;

if (_T_C < 0 && _rain > 0) then {
    // Warm-layer proxy: thick overcast + low altitude
    private _altitude = missionNamespace getVariable [QEGVAR(core,referenceAltitude), 0];
    if !(_altitude isEqualType 0) then { _altitude = 0; };

    if (overcast > 0.6 && _altitude < 500) then {
        _isFreezing = true;
        // Severity scales with rain rate and how far below zero
        _severity = _rain * ((0 - _T_C) / 10) min 1;
    };
};

missionNamespace setVariable [QEGVAR(core,currentFreezingRain),  _isFreezing];
missionNamespace setVariable [QEGVAR(core,currentIcingSeverity), _severity];

_isFreezing
