#include "..\script_component.hpp"

/*
Proportional navigation acceleration command (pure).

    a_cmd = N' * Vc * lambda_dot

    N'          navigation constant (dimensionless)
    Vc          closing velocity, m/s
    lambda_dot  line-of-sight rate, rad/s

The command is applied PERPENDICULAR to the line of sight, in the plane of
the LOS rotation.  This kernel returns the command MAGNITUDE; the caller
applies it along the perpendicular.  A positive closing velocity and a
positive LOS rate give a positive command.

N' = 3 is the theoretical minimum; 4 to 5 is the common design band (4 is the
usual design point).  N' is a tuning value, not a measured constant.

SOURCE.  Zarchan, "Tactical and Strategic Missile Guidance", AIAA Progress in
Astronautics and Aeronautics: 5th ed. vol. 219 (2007, ISBN 1-56347-874-9),
6th ed. vol. 239 (2012, ISBN 978-1-60086-894-8), 7th ed. vol. 258/259 (2019,
ISBN 978-1-62410-537-1).  Also Zarchan, "Proportional Navigation and Weaving
Targets", J. Guidance Control Dyn. 18(5):969-974, 1995, DOI 10.2514/3.21492.
The issue #131 vector "9g weave at 1 rad/s -> ~88 m miss" is the WEAVE
AMPLITUDE implied by a = A * omega^2 (A = 88.26 / 1 = 88.3 m), not a PN miss
distance; the attribution of that figure to Zarchan is UNVERIFIED.

Arguments:
  0: _navConstant      (NUMBER) N', default 4, >= 0
  1: _closingVelocity  (NUMBER) Vc, m/s
  2: _losRate          (NUMBER) lambda_dot, rad/s
  3: _maxAccel         (NUMBER) command clamp, m/s2; <= 0 disables the clamp

Return Value: NUMBER - commanded acceleration in m/s2, clamped to
[-maxAccel, +maxAccel] when a positive clamp is given.
Public: No
*/

params [
    ["_navConstant", 4, [0]],
    ["_closingVelocity", 0, [0]],
    ["_losRate", 0, [0]],
    ["_maxAccel", 0, [0]]
];

private _command = _navConstant * _closingVelocity * _losRate;

if (_maxAccel > 0) then {
    _command = (_command max (0 - _maxAccel)) min _maxAccel;
};

_command
