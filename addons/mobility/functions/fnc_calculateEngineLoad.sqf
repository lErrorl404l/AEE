#include "..\script_component.hpp"

/*
Engine load fraction from tractive power demand and acceleration.

WHY THIS FUNCTION EXISTS.  A road vehicle has no numeric throttle reader in
this engine.  collectiveRTD is rotary and throttleRTD is fixed wing, so a
LandVehicle reads neither.  getInfo is absent from the client binary.  AEE's
own mobility model holds no engine load reader either: fnc_calculateTraction
takes no throttle and works from ground speed, wheel speed, slip, mass and
surface, and the only enginePower in the repository is a PhysX tuning value
used as an input to a mass estimate.  Engine load is therefore DERIVED from a
physical power balance.  It is NOT a measurement of the engine.

THE PHYSICS.  Engine load is proportional to the power the engine must
deliver.  For a road vehicle that is the tractive power plus the power to
accelerate the inertia:

  drag force        F_drag = 0.5 rho Cd A v^2                     [N]
  resistance force  F_res  = F_traction + F_grade + F_drag        [N]
  tractive demand          = F_res * v                            [W]
  inertial demand          = m * a * v                            [W]
  load fraction            = (tractive + inertial) / P_rated      [-]

Units: force in N and speed v in m/s, so force times speed is W.  Mass m in
kg and acceleration a in m/s^2 give m a in N, and the inertial POWER is
m a v in W.  Density rho is kg/m^3 and the drag area Cd A is m^2, so
0.5 rho Cd A v^2 is N.

THE RESISTANCE FORCE.  F_traction is the published QGVAR(tractionForce) from
fnc_calculateTraction, which is the traction coefficient times the mass, and
the caller reads it.  F_grade is caller supplied and defaults to zero,
because AEE holds no reusable terrain gradient reader:
fnc_calculateTerrainLimits and fnc_calculateRolloverThreshold both TAKE a
slope as an argument and neither publishes one, so this kernel would
otherwise have to invent a terrain query.  The aerodynamic term is a
DECLARED DEFAULT, because no per-vehicle drag coefficient or frontal area
exists in the repository.  The drag area defaults to a nominal 0.7 m^2.  It
is a declared default, not a measurement.

RATED POWER IS A DECLARED DEFAULT.  fnc_estimateVehicleMassCore holds power
band bounds, but they are inputs to a mass estimate, and the only
per-vehicle power is the config key enginePower, a PhysX tuning value with
no verified real-world unit.  No rated power in watts is reachable, so the
kernel takes one as an argument with a declared default of 150000 W for a
light road vehicle.

A STATIONARY VEHICLE AT HIGH RPM CANNOT BE DISTINGUISHED FROM A STATIONARY
VEHICLE AT IDLE.  The engine publishes no rpm for a road vehicle, and at
zero speed the tractive and inertial terms both vanish.  The kernel
therefore returns the declared idle fraction rather than a hard zero, and
the caller reaches it only for a vehicle whose engine is on.  That is a
LIMIT OF THE ENGINE, not an approximation this function chose.

THE OBJECT-SIDE WORK IS THE CALLER'S.  Reading the published traction force,
differencing the velocity between ticks, and supplying the mass, the rated
power, the gradient term and the drag area all belong to the renderer.  This
function is PURE ARITHMETIC over scalars, which is what lets the headless
harness sweep the curve with no vehicle.

Guards, each explicit:
  - A non-positive rated power is refused with -1, because dividing by it is
    undefined.
  - A non-positive mass is refused with -1, because the inertial term then
    vanishes and the result would silently mean a different vehicle.
  - The returned fraction is clamped to 0..1.
  - The fraction is floored at the declared idle fraction while the engine
    runs, so an engine at rest shows a small plume rather than none.

Arguments:
  0:  _tractionForceN  (NUMBER) tractive resistance force, N
  1:  _speedMS         (NUMBER) forward speed, m/s, made a magnitude
  2:  _massKg          (NUMBER) vehicle mass, kg, > 0
  3:  _accelerationMS2 (NUMBER) longitudinal acceleration, m/s^2
  4:  _ratedPowerW     (NUMBER) rated engine power, W, > 0
  5:  _idleFraction    (NUMBER) declared idle load floor, 0..1
  6:  _gradeForceN     (NUMBER) caller-supplied gradient resistance, N
  7:  _airDensity      (NUMBER) air density, kg/m^3
  8:  _dragAreaM2      (NUMBER) declared drag area Cd*A, m^2

Return Value: NUMBER, the load fraction in 0..1, or -1 when an input is
unusable.
Example: [1700, 30, 2000, 0.5, 150000, 0.05] call aee_mobility_fnc_calculateEngineLoad
Public: No
*/

params [
    ["_tractionForceN", 0, [0]],
    ["_speedMS", 0, [0]],
    ["_massKg", 0, [0]],
    ["_accelerationMS2", 0, [0]],
    ["_ratedPowerW", 150000, [0]],
    ["_idleFraction", 0.05, [0]],
    ["_gradeForceN", 0, [0]],
    ["_airDensity", 1.225, [0]],
    ["_dragAreaM2", 0.7, [0]]
];

// A non-positive rated power cannot be divided by, and a non-positive mass
// removes the inertial term so the result would mean a different vehicle.
if (_ratedPowerW <= 0) exitWith { -1 };
if (_massKg <= 0) exitWith { -1 };

private _speed = abs _speedMS;
private _rho = _airDensity max 0;

private _dragN = 0.5 * _rho * _dragAreaM2 * _speed * _speed;
private _resistanceN = _tractionForceN + _gradeForceN + _dragN;
private _tractiveW = _resistanceN * _speed;
private _inertialW = _massKg * _accelerationMS2 * _speed;
private _load = (_tractiveW + _inertialW) / _ratedPowerW;

// The idle floor is the declared minimum while the engine runs.
private _idle = _idleFraction max 0 min 1;
_load = (_load max _idle) min 1;

_load
