#include "..\..\script_component.hpp"

/*
Station pressure from the sea-level pressure and elevation (hypsometric equation).

  P_station = P_sea * (1 - lapse_per_m * elevation / T_std) ^ exponent

The lapse rate is degrees Celsius per 1000 m, so it is divided by 1000 to get
kelvin per metre before it enters the formula.  The ratio is floored at 0.05 to
keep the power finite far above the tropopause.

Pure: no missionNamespace, no GVAR or EGVAR, no engine command.  The driver
FUNC(updatePressure) reads the state, calls this kernel and rounds the result.

Arguments:
  0: Number - sea-level pressure, hPa
  1: Number - elevation above sea level, m
  2: Number - temperature lapse rate, degrees Celsius per 1000 m

Returns:
  Number - station pressure, hPa (unrounded)
*/

params [
    ["_P_sea", ISA_SEA_LEVEL_PRESSURE_HPA, [0]],
    ["_elevation", 0, [0]],
    ["_lapseRate", 6.5, [0]]
];

private _T_std = 288.15;
private _exponent = 5.2559;
private _ratioFloor = 0.05;

private _lapsePerM = _lapseRate / 1000;
private _ratio = (1 - (_lapsePerM * _elevation / _T_std)) max _ratioFloor;

_P_sea * (_ratio ^ _exponent)
