#include "..\script_component.hpp"
/*
Road-load force and drive power from the road-load equation (issue #111).

WHY THIS FUNCTION EXISTS.  The fuel model needs the power the engine must
deliver to hold a road speed.  That power is the road-load force times the
speed.  The force is the published road-load equation (Gillespie, Fundamentals
of Vehicle Dynamics):

  F = C_rr * m * g                     rolling resistance
    + 0.5 * rho * Cd * A * v^2         aerodynamic drag
    + m * g * sin(theta)               grade
    + m * a                            inertia

The drag term is the SAME form the existing engine-load kernel
aee_vehicles_fnc_calculateEngineLoad uses, and the inertial term is the same
m*a term.  This kernel does not build a second vehicle-dynamics model: it is
the road-load force the fuel chain consumes, with the rolling-resistance and
grade terms the engine-load kernel leaves to its caller.

P_drive = F * v, in watts, because force is in N and speed is in m/s.

THE GRADE IS THE CALLER'S.  AEE holds no reusable terrain-gradient reader:
aee_mobility_fnc_calculateTerrainLimits and fnc_calculateRolloverThreshold
both TAKE a slope and neither publishes one.  So the caller supplies
sin(theta), the sine of the incline, positive climbing.  A vehicle's own pitch
sine (the z component of vectorDir) is the natural source.

THE DRAG AREA IS THE CALLER'S.  No per-vehicle Cd or frontal area exists in
the repository, so the caller supplies Cd*A.  The declared default is the same
0.7 m^2 the engine-load kernel declares.

Guards, each explicit:
  - A non-positive mass is refused with [-1, -1]: the rolling and grade terms
    vanish and the result would mean a different vehicle.
  - A negative rolling coefficient, drag area or air density is refused with
    [-1, -1]: each is a physical magnitude.
  - The speed is made a magnitude, so a reverse speed reads the same load.

Arguments:
  0: _massKg       (NUMBER) vehicle mass, kg, > 0
  1: _speedMS      (NUMBER) forward speed, m/s
  2: _accelMS2     (NUMBER) longitudinal acceleration, m/s^2
  3: _crr          (NUMBER) rolling-resistance coefficient, >= 0
  4: _gradeSin     (NUMBER) sine of the incline, positive climbing
  5: _dragAreaM2   (NUMBER) declared Cd*A, m^2, >= 0
  6: _airDensity   (NUMBER) air density, kg/m^3, >= 0

Return Value: ARRAY - [forceN, drivePowerW], or [-1, -1] when an input is
unusable.
Example: [2361, 22.2, 0, 0.007, 0, 0.7, 1.225] call aee_vehicles_fnc_calculateRoadLoad
Public: No
*/

params [
    ["_massKg", 0, [0]],
    ["_speedMS", 0, [0]],
    ["_accelMS2", 0, [0]],
    ["_crr", 0, [0]],
    ["_gradeSin", 0, [0]],
    ["_dragAreaM2", 0.7, [0]],
    ["_airDensity", 1.225, [0]]
];

if (_massKg <= 0) exitWith { [-1, -1] };
if (_crr < 0 || _dragAreaM2 < 0 || _airDensity < 0) exitWith { [-1, -1] };

private _g = 9.80665;   // standard gravity, m/s^2
private _speed = abs _speedMS;

private _rollingN = _crr * _massKg * _g;
private _aeroN = 0.5 * _airDensity * _dragAreaM2 * _speed * _speed;
private _gradeN = _massKg * _g * _gradeSin;
private _inertiaN = _massKg * _accelMS2;

private _forceN = _rollingN + _aeroN + _gradeN + _inertiaN;
private _drivePowerW = _forceN * _speed;

[_forceN, _drivePowerW]
