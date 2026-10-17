#include "..\..\script_component.hpp"
/*
Relative humidity now, from the climate's mean humidity and the diurnal
temperature.

The day's mean relative humidity is the station normal interpolated
between mid-month values; the air's vapour pressure is held at the day's
value and the relative humidity follows the temperature
(fnc_calculateRelativeHumidity: RH = 100 e / e_w(T)).  The day's mean
temperature is published by fnc_updateTemperature (the same normals and
height).

Stored in QEGVAR(core,currentHumidity).
*/
params [
    ["_biome", "Cfa", [""]],
    ["_month", 1, [0]],
    ["_posASL", [], [[]]]
];
private _normals = [_biome] call EFUNC(weather,getClimateNormals);
private _rhArr = _normals select 4;
date params ["_dy", "_dm", "_dd"];
private _midFrac = (_dd - 15.2) / 30.44;
private _m0 = (_dm - 1) + (floor _midFrac);
private _w = _midFrac - (floor _midFrac);
private _i0 = ((_m0 mod 12) + 12) mod 12;
private _i1 = (_i0 + 1) mod 12;
private _rhMean = ((_rhArr select _i0) * (1 - _w)) + ((_rhArr select _i1) * _w);

private _tNow = missionNamespace getVariable [QEGVAR(core,currentTemperature), 15];
if !(_tNow isEqualType 0) then { _tNow = 15; };
private _tMean = missionNamespace getVariable [QEGVAR(core,currentDayMeanTemp), _tNow];
if !(_tMean isEqualType 0) then { _tMean = _tNow; };

// The kernel is dispatched to the native twin when the dev extension is
// ready and runs the SQF reference otherwise; both are the same formula.
private _rh = ["calculateRelativeHumidity", [_rhMean, _tMean, _tNow]] call EFUNC(core,dispatchKernel);
if (_rh isEqualType "") then { _rh = parseNumber _rh; };
if !(_rh isEqualType 0) then {
    _rh = [_rhMean, _tMean, _tNow] call FUNC(calculateRelativeHumidity);
};
missionNamespace setVariable [QEGVAR(core,currentHumidity), _rh];
missionNamespace setVariable [QEGVAR(core,currentVapourPressure), (_rhMean / 100) * 6.112 * exp (17.62 * _tMean / (243.12 + _tMean))];
_rh
