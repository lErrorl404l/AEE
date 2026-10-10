#include "..\script_component.hpp"
/*
Brake-specific fuel consumption rate from engine power (issue #111).

  fuel_L_h = BSFC[g/kWh] * P[kW] / rho_fuel[g/L]

The units close: BSFC * P is g/h, and g/h over g/L is L/h.  P is the idle
power plus the drive power, in kW.

THE SFC RELATION IS THE REPOSITORY'S.  The aircraft fuel kernel
aee_flight_fnc_calculateFuelBurn already converts a specific fuel consumption
to a mass rate:

  fuel_burn_kg_s = sfc_kg_kwh * rated_power_w / 3.6e6

This kernel is the same relation in the ground units the brief states (BSFC in
g/kWh, power in kW, the answer in L/h).  It is the ground sibling of that
kernel, not a second model of a different physics.  The mass rate it also
returns is the fuel flow the coolant heat balance consumes.

THE BSFC IS A BEST-POINT SCALAR, NOT A FULL MAP.  The brief models a class as
one scalar plus a load curve, not a two-dimensional map.  This kernel applies
the scalar to the power demand; the load curve is the caller's, because a
part-load BSFC penalty is a per-class calibration the corpus does not hold.

Guards, each explicit:
  - A negative BSFC is refused with [-1, -1].
  - A non-positive fuel density is refused with [-1, -1], because the litres
    divide by it.
  - The idle and drive powers are floored at zero: a negative power is not a
    load.

Arguments:
  0: _idlePowerW    (NUMBER) idle power, W, >= 0
  1: _drivePowerW   (NUMBER) drive power, W, >= 0
  2: _bsfcGKwh      (NUMBER) brake-specific fuel consumption, g/kWh, >= 0
  3: _fuelDensityGL (NUMBER) fuel density, g/L, > 0

Return Value: ARRAY - [fuelRateLph, fuelMassRateKgs], or [-1, -1] when an
input is unusable.
Example: [7500, 8300, 206, 840] call aee_vehicles_fnc_calculateFuelRate
Public: No
*/

params [
    ["_idlePowerW", 0, [0]],
    ["_drivePowerW", 0, [0]],
    ["_bsfcGKwh", 0, [0]],
    ["_fuelDensityGL", 0, [0]]
];

if (_bsfcGKwh < 0) exitWith { [-1, -1] };
if (_fuelDensityGL <= 0) exitWith { [-1, -1] };

private _powerKW = ((_idlePowerW max 0) + (_drivePowerW max 0)) / 1000;
private _fuelRateLph = _bsfcGKwh * _powerKW / _fuelDensityGL;
private _fuelMassRateKgs = _fuelRateLph * _fuelDensityGL / 3.6e6;

[_fuelRateLph, _fuelMassRateKgs]
