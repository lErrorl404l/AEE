#include "..\script_component.hpp"

/*
Vehicle rollover threshold from the Static Stability Factor (issue #108).

The physics is pure and has no engine dependency, so it is separated from
the per-frame applier and evaluated in the Python suite against the
published formulas.

  Static Stability Factor   SSF = T / (2 h)
    T is the track width, h the centre-of-gravity height.  SSF is the
    lateral acceleration in g at which the inside wheels lift on LEVEL
    ground.  Source: NHTSA Rollover Resistance rating (SSF definition).

  Slope correction.  On a banked surface the lateral and gravitational
  components add, so the threshold falls:
    a_crit = g (SSF cos(theta) - sin(theta))
    Source: Gillespie, Fundamentals of Vehicle Dynamics, eq. [4]
    (ROSAP DOT 36415); the same form is in ERDC TR-05-6 and
    STO-TR-AVT-248 for NRMM side-slope stability.

  Dynamic factor.  A real manoeuvre reaches 70 to 90 percent of the static
  threshold before the inside wheels lift (body roll, tyre deflection,
  load transfer).  The default is 0.8:
    a_applied = 0.8 * a_crit

Both thresholds are returned, because they answer different questions and
the issue quotes both: 0.69 g is the static slope-corrected value at
SSF 1.1 and 20 degrees, and the 0.8 factor is then applied on top.

The steady-turn form follows from a_lat = V^2 / R:
    V_crit = sqrt(g R SSF)   on level ground.

Arguments:
  0: ssf (NUMBER)          - static stability factor, dimensionless
  1: slopeDeg (NUMBER)     - ground slope across the track, degrees
  2: dynamicFactor (NUMBER)- fraction of static reached, 0.7 to 0.9

Return Value: ARRAY [staticG, appliedG, dynamicFactor]
Example: [1.1, 20, 0.8] call aee_mobility_fnc_calculateRolloverThreshold
Public: No
*/

params [
    ["_ssf", 0, [0]],
    ["_slopeDeg", 0, [0]],
    ["_dynamicFactor", 0.8, [0]]
];

// A vehicle with no SSF (an unreadable config) has no threshold; return
// zero so the caller's test a_lat > 0 is false and nothing fires.
if (_ssf <= 0) exitWith { [0, 0, _dynamicFactor] };

_dynamicFactor = _dynamicFactor max 0.1 min 1.0;

private _theta = _slopeDeg * 0.0174532925;   // SQF atan works in degrees

// The slope term can exceed the SSF term on a steep bank, which makes the
// threshold negative: the vehicle tips on the slope alone.  Clamp at zero
// so the comparison stays a real number.
private _staticG = (_ssf * cos _theta) - (sin _theta);
if (_staticG < 0) then { _staticG = 0; };

private _appliedG = _staticG * _dynamicFactor;

[_staticG, _appliedG, _dynamicFactor]
