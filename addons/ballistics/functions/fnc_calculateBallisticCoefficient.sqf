#include "..\script_component.hpp"
/*
Ballistic coefficient calculation (issue #167).

CALCULATES a round's ballistic coefficient from its physical inputs and
bullet shape - NOT a lookup.  The G1 reference-density formula:

  BC = m / (i * d^2)

  m - the bullet mass in POUNDS
  i - the form factor (the shape's drag efficiency relative to the G1
      reference spitzer: i = 1.0 for a G1 FMJ, 0.75 for a G7 VLD
      boat-tail - the lower the form factor, the lower the drag)
  d - the bullet diameter in INCHES

This is the standard ballistics formula (Litz "Applied Ballistics",
McCoy "Modern Exterior Ballistics"): the BC is the sectional density
(m/d^2) divided by the form factor.  A round's BC follows from its
mass, diameter, and shape class - the shape classifier resolves the
form factor, and the config gives the mass + diameter.

The result is the G1 BC.  A G7 BC is converted by the G1/G7 ratio
(~0.43-0.50 for boat-tail match bullets: BC_G7 = BC_G1 * 0.47
approximately, the standard conversion).

Arguments:
  0: massG (NUMBER, the projectile mass in grams)
  1: caliberMm (NUMBER, the bullet diameter in mm)
  2: formFactor (NUMBER, the shape's form factor i; default 1.0)
  3: asG7 (BOOLEAN, return the G7 BC instead of G1, default false)

Returns the ballistic coefficient.
*/
params ["_massG", "_caliberMm", ["_formFactor", 1.0, [0]], ["_asG7", false, [false]]];
if (_massG <= 0 || _caliberMm <= 0 || _formFactor <= 0) exitWith { 0 };

// The mass in pounds (1 lb = 453.592 g), the diameter in inches.
private _massLb = _massG / 453.592;
private _diamIn = _caliberMm / 25.4;

// BC = m / (i * d^2)
private _bc = _massLb / (_formFactor * (_diamIn ^ 2));

// The G7 conversion (the real ratio: M118LR 0.49, Mk262 0.54 - the
// ~0.52 average for boat-tail match bullets).
if (_asG7) then { _bc = _bc * 0.52; };

_bc
