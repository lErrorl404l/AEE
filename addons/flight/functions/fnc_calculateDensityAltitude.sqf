#include "..\script_component.hpp"

/*
Density altitude from pressure altitude and outside air temperature.

Density altitude is the height in the ICAO standard atmosphere (ICAO Doc
7488 / ISO 2533: T0 288.15 K, p0 101325 Pa, L 0.0065 K/m, R 287.053 J/kg/K,
g 9.80665) at which the standard density equals the actual density.  The
actual density follows from the pressure at the pressure altitude and the
outside air temperature, rho = p / (R T); the ISA troposphere then inverts
exactly:
    p  = p0 (1 - L PA / T0)^(g / (R L))
    DA = (T0 / L) (1 - (rho / rho0)^(R L / (g - R L)))
(The FAA rule of thumb, 120 ft per degree C off ISA, linearises this; the
exact form is used.)
This is a pure kernel: no missionNamespace, no GVAR or EGVAR, no engine
command.

Arguments:
  0: NUMBER - pressure altitude, metres
  1: NUMBER - outside air temperature, degrees Celsius

Return Value: NUMBER - density altitude, metres
Example: [2400, 30] call aee_flight_fnc_calculateDensityAltitude
Public: No
*/

params [
    ["_pressureAltitudeM", 0, [0]],
    ["_oatC", 15, [0]]
];

private _t0 = 288.15;
private _lapse = 0.0065;
private _r = 287.053;
private _g = 9.80665;
private _p = 101325 * ((1 - _lapse * _pressureAltitudeM / _t0) ^ (_g / (_r * _lapse)));
private _rho = _p / (_r * (_oatC + 273.15));
private _rho0 = 101325 / (_r * _t0);
(_t0 / _lapse) * (1 - ((_rho / _rho0) ^ ((_r * _lapse) / (_g - _r * _lapse))))
