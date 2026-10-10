#include "..\script_component.hpp"

/*
Turbulence force magnitude for one aircraft, one tick.

The gust is a relative wind.  The force it exerts is aerodynamic drag:

  dynamic pressure  q = 0.5 rho v^2                     [Pa]
  drag force        F = q * (Cd S)                      [N]

rho is the local air density in kg/m^3, v the gust velocity in m/s, and Cd S
the airframe's effective drag area in m^2.  The caller supplies the drag area
from the aircraft corpus record; the reference it comes from is stated there
(data/aircraft/SCHEMA.md section 5).  This is the same drag relation the air
engine load kernel uses for a wing.

The force does NOT carry the mass, so the acceleration it realises is F / mass:
a heavy airframe resists a gust and a light one is nudged.  That is the point
of the fix.  The old kernel multiplied by the mass, so the acceleration was the
same for every airframe.

The result is capped at TURBULENCE_FORCE_CAP_FRACTION (0.25) of the aircraft
weight, so an extreme gust stays a perturbation and never dominates.

Arguments:
  0: NUMBER - gust velocity magnitude, m/s, >= 0
  1: NUMBER - air density, kg/m^3, > 0
  2: NUMBER - effective drag area Cd S, m^2, >= 0
  3: NUMBER - aircraft mass, kg, > 0

Return Value: NUMBER - force magnitude in N, 0 or more
Example: [4, AERO_ISA_SEA_LEVEL_DENSITY, 0.7, 1200] call aee_flight_fnc_calculateTurbulenceForce
Public: No
*/

params [
    ["_gustMS", 0, [0]],
    ["_densityKgM3", AERO_ISA_SEA_LEVEL_DENSITY, [0]],
    ["_dragAreaM2", 0, [0]],
    ["_massKg", 0, [0]]
];

if (_massKg <= 0) exitWith { 0 };
if (_gustMS <= 0) exitWith { 0 };
if (_dragAreaM2 <= 0) exitWith { 0 };

private _gust = _gustMS max 0;
private _rho = (_densityKgM3 max 0) min (AERO_ISA_SEA_LEVEL_DENSITY * TURBULENCE_DENSITY_RATIO_MAX);
private _forceN = 0.5 * _rho * _gust * _gust * _dragAreaM2;

// Weight-relative cap: a gust force stays a perturbation, never the driver.
private _capN = _massKg * STANDARD_GRAVITY * TURBULENCE_FORCE_CAP_FRACTION;

(_forceN min _capN) max 0
