#include "..\script_component.hpp"

/*
Air density from temperature, pressure and relative humidity.

Step 1 - saturation vapour pressure (Buck 1996):
  e_s = 6.1121 * exp((18.678 - T/234.5) * T / (257.14 + T))
Step 2 - actual vapour pressure: e = e_s * RH / 100
Step 3 - virtual temperature: T_v = T_K / (1 - 0.37802 * e / P_hPa)
Step 4 - density: rho = P_Pa / (R_d * T_v),  R_d = 287.05287 J/(kg K)

Pure: no missionNamespace, no GVAR or EGVAR, no engine command.  The driver
FUNC(calculateAirDensity) reads the weather state, calls this kernel and stores
the result.

Arguments:
  0: Number - air temperature, degrees Celsius
  1: Number - pressure, hPa
  2: Number - relative humidity, %

Returns:
  Number - air density, kg/m3
*/

params [
    ["_T_C", 15, [0]],
    ["_P_hPa", 1013, [0]],
    ["_RH", 50, [0]]
];

private _buckA = 6.1121;
private _buckB = 18.678;
private _buckC = 234.5;
private _buckD = 257.14;
private _virtualTempCoef = 0.37802;
private _kelvinOffset = 273.15;
private _specificGasDry = 287.05287;
private _paPerHpa = 100;

private _e_s = _buckA * exp ((_buckB - _T_C / _buckC) * _T_C / (_buckD + _T_C));
private _e = _e_s * _RH / 100;
private _T_K = _T_C + _kelvinOffset;
private _T_v = _T_K / (1 - _virtualTempCoef * _e / _P_hPa);
private _P_Pa = _P_hPa * _paPerHpa;

_P_Pa / (_specificGasDry * _T_v)
