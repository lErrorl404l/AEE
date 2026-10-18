#include "..\script_component.hpp"

/*
Standard (pressure-corrected) altitude kernel.

The altimeter HUD prints this field in metres, so the pressure correction
factor must be metres per hPa.  ICAO standard atmosphere, hydrostatic at sea
level: dz/dp = 1 / (rho0 * g), so one hPa is 100 / (rho0 * g) =
100 / (AERO_ISA_SEA_LEVEL_DENSITY * STANDARD_GRAVITY) = 8.325 m (27.3 ft).
The factor is derived here from the two shared constants rather than written
as a second literal, so one definition states the fact.

Why 8.325 m and not the 30 ft/hPa aviation rule of thumb (9.144 m): the rule
of thumb is a lower-precision figure for the 950-1050 hPa altimeter-setting
band, and a foot figure applied to a metre altitude without conversion is the
defect this kernel removes (issue #294, a factor of 3.6).  The hydrostatic
value matches the ISA pressure-altitude relation in
FUNC(calculateQNH) and the issue's vector of 83 m per 10 hPa.

Valid in the lower troposphere, where the altimeter is used.

Pure: no missionNamespace, no GVAR or EGVAR, no engine command.

Arguments:
  0: Number - indicated altitude, metres
  1: Number - current sea-level pressure (QNH), hPa

Returns:
  Number - standard altitude, metres
*/

params [
    ["_altitude_m", 0, [0]],
    ["_pressure_hPa", ISA_SEA_LEVEL_PRESSURE_HPA, [0]]
];

private _paPerHpa = 100;
private _airDensity = AERO_ISA_SEA_LEVEL_DENSITY;
private _gravity = STANDARD_GRAVITY;
private _metresPerHpa = _paPerHpa / (_airDensity * _gravity);

_altitude_m + (ISA_SEA_LEVEL_PRESSURE_HPA - _pressure_hPa) * _metresPerHpa
