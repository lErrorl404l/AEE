#include "..\script_component.hpp"

/*
Turbulence force magnitude for one aircraft, one tick.

The gust target is a velocity in m/s.  The force that realises it is the
mass times the demanded acceleration.  TURBULENCE_FORCE_DIVISOR (100) is
the conversion the simple-model velocity path already used; it is UNSOURCED
calibration, not a measured coefficient.  Density scales the force, because
the same gust moves thin air less.

The result is capped at TURBULENCE_FORCE_CAP_FRACTION (0.25) of the
aircraft weight, so an extreme gust can never dominate the airframe.

Arguments:
  0: NUMBER - gust target magnitude, m/s, >= 0
  1: NUMBER - density ratio rho / 1.225, > 0
  2: NUMBER - aircraft mass, kg, > 0

Return Value: NUMBER - force magnitude in N, 0 or more
Example: [4, 1.0, 1200] call aee_mobility_fnc_calculateTurbulenceForce
Public: No
*/

params [
    ["_gustMS", 0, [0]],
    ["_densityRatio", 1, [0]],
    ["_massKg", 0, [0]]
];

if (_massKg <= 0) exitWith { 0 };
if (_gustMS <= 0) exitWith { 0 };

private _gust = _gustMS max 0;
private _rho = (_densityRatio max 0) min TURBULENCE_DENSITY_RATIO_MAX;
private _forceN = (_gust * _rho * _massKg) / TURBULENCE_FORCE_DIVISOR;

// Weight-relative cap: a gust force stays a perturbation, never the driver.
private _capN = _massKg * 9.80665 * TURBULENCE_FORCE_CAP_FRACTION;

(_forceN min _capN) max 0
