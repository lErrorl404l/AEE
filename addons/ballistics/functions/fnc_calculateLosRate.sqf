#include "..\script_component.hpp"

/*
Line-of-sight rate (pure).

    lambda_dot = acos( clamp( u_prev . u_now, -1, 1 ) ) / dt

    u_prev, u_now  line-of-sight unit vectors on consecutive ticks
    dt             time between the two samples, s

The angle between two unit vectors is acos of their dot product; dividing by
the elapsed time gives the angular rate.  The dot product is clamped to
[-1, 1] before acos because a rounding error can push it just outside that
range and acos of a value above 1 is NaN.  The returned magnitude is what the
proportional-navigation kernel consumes as lambda_dot.

Arma's acos returns DEGREES (fnc_calculateRouteDegradation and
fnc_calculateMachCone rely on this), so the result is converted to radians
before it is divided by the time.  The PN kernel expects lambda_dot in rad/s.

This is the plain angular rate of the LOS vector.  It is signed only by the
caller: this kernel returns the magnitude, and the caller applies the PN
command along the perpendicular to the LOS in the plane of rotation.

Arguments:
  0: _prevLos (ARRAY) previous LOS unit vector, [x, y, z]
  1: _nowLos  (ARRAY) current LOS unit vector, [x, y, z]
  2: _dt      (NUMBER) elapsed time, s, > 0

Return Value: NUMBER - LOS rate magnitude in rad/s.  Returns 0 when dt is not
positive or either vector is empty.
Public: No
*/

params [
    ["_prevLos", [0, 0, 0], [[]]],
    ["_nowLos", [0, 0, 0], [[]]],
    ["_dt", 0, [0]]
];

if (_dt <= 0) exitWith { 0 };
if ((count _prevLos) < 3) exitWith { 0 };
if ((count _nowLos) < 3) exitWith { 0 };

private _dot = (_prevLos vectorDotProduct _nowLos) max (0 - 1) min 1;

// acos returns degrees; convert to radians for the rad/s contract.
private _rateRad = (acos _dot) * pi / 180;

_rateRad / _dt
