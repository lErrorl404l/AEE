#include "..\script_component.hpp"

/*
Engine load fraction for an AIR vehicle, from a real power balance.

WHY THIS FUNCTION EXISTS.  An aircraft has no usable engine-power reader in
this engine.  The RotorLib real-time data interface returns collectiveRTD for a
helicopter and throttleRTD for fixed wing, but the group reports a meaningful
value ONLY when the advanced flight model is on, which the code tests with
difficultyEnabledRTD.  A client running the SIMPLE flight model has that
setting false, so the reader is skipped, and an aircraft is not a LandVehicle,
so the derived ground term in fnc_calculateEngineLoad is skipped too.  An
aircraft then falls through to the declared idle for the whole flight, however
hard it climbs.  This kernel is the missing AIR term.  It is DERIVED from a
power balance and is NOT a measurement of the engine.

A FIXED-WING AIRCRAFT AND A ROTARY ONE ARE DIFFERENT MACHINES.  A wing makes
lift with forward speed and its engine overcomes drag, so its delivered power
rises with the CUBE of airspeed.  A rotor makes lift while stationary and its
engine overcomes the weight of the aircraft through induced flow.  The two
balances cannot be the same equation without inventing physics, so the kernel
branches on the class the caller passes and uses the balance that fits.

THE PHYSICS, WING (a Plane).  In steady level flight thrust equals drag, so
the power the engine delivers is the drag power:

  drag force   D = 0.5 rho Cd S v^2                 [N]
  drag power   P = D * v = 0.5 rho (Cd S) v^3       [W]
  fraction     = P / P_rated                        [-]

The product Cd S is the effective drag AREA in m^2.  rho is kg/m^3 and v is
m/s, so 0.5 rho Cd S v^2 is N and multiplying by v gives W.

THE PHYSICS, ROTOR (a Helicopter).  Momentum theory gives the IDEAL induced
power to hold the aircraft in hover:

  weight        W = m g                             [N]
  induced vel   v_i = sqrt (W / (2 rho A))          [m/s]
  hover power   P = W v_i = W^1.5 / sqrt (2 rho A)  [W]
  fraction      = P / P_rated                       [-]

A is the rotor disc area in m^2 and g is standard gravity, STANDARD_GRAVITY m/s^2, the
same value fnc_applyRollover uses.  THIS IS AN IDEAL LOWER BOUND, NOT A
MEASUREMENT.  A real rotor also spends power on profile drag and on the tail
rotor, and a helicopter in forward flight additionally overcomes parasite
drag, so the true hover fraction is HIGHER than the ideal figure here.  The
bound is stated rather than hidden.  The rotor term does not depend on forward
speed, because the formula is the hover balance; a forward-flight term would
need a different derivation and is deliberately not invented.

WORKED REFERENCE, WING.  Piper PA-28-181: mass 1100 kg, wing area 16.16 m^2,
span 11.0 m, rated power 134 kW, maximum level speed 58 m/s.  Aspect ratio
AR = 11.0^2 / 16.16 = 7.49.  Lift coefficient CL = 2 W / (rho v^2 S) =
21582 / (AERO_ISA_SEA_LEVEL_DENSITY * 3364 * 16.16) = 0.324.  Induced drag CDi = CL^2 / (pi AR e)
with e = 0.8 is 0.0056, and with a zero-lift CD0 of 0.037 the total is
CD = 0.0426.  Cd S = 0.0426 * 16.16 = 0.688 m^2.  D = 0.5 rho Cd S v^2 =
1418 N, so P = 1418 * 58 = 82.2 kW and the fraction is 82.2 / 134 = 0.61.

WORKED REFERENCE, ROTOR.  Robinson R44: mass 580 kg, rotor disc 81 m^2, rated
power 131 kW.  W = 580 * STANDARD_GRAVITY = 5688 N.  P = 5688^1.5 / sqrt (2 * AERO_ISA_SEA_LEVEL_DENSITY *
81) = 30.5 kW, so the fraction is 30.5 / 131 = 0.23.  This is the ideal
induced power and a lower bound, as above.

THE DRAG AREA AND THE ROTOR DISC AREA ARE DECLARED DEFAULTS, NOT
MEASUREMENTS.  No per-vehicle drag coefficient or rotor disc area exists in
this repository in a verified real-world unit, so the kernel takes both as
arguments with declared defaults.  The drag area default is a nominal 0.7 m^2,
the same nominal figure fnc_calculateEngineLoad uses, and the PA-28 above
independently gives 0.688 m^2.  THAT AGREEMENT IS A COINCIDENCE OF ORDER OF
MAGNITUDE, NOT EVIDENCE that an aircraft and a road vehicle share a drag area;
a light aircraft and a light car happen to land near the same figure.  The
rotor disc default is 50 m^2, a light helicopter, because a Robinson R22 rotor
disc is 7.76 m across, which is 47 m^2.

RATED POWER IS A DECLARED DEFAULT.  The kernel takes one as an argument with a
default of 150000 W, the same default as the ground kernel.  The caller reads
the optional per-vehicle variable aee_engineRatedPowerW and passes it, so a
mission can state the real value; there is no second rated-power variable.

THE OBJECT-SIDE WORK IS THE CALLER'S.  Reading the class with typeOf, the
mass with getMass, the speed with velocity, the published air density, and the
per-vehicle overrides all belong to the renderer.  This function is PURE ARITHMETIC
over scalars plus one class test, which is what lets the headless harness call
it directly with no vehicle.
Guards, each explicit:
  - A non-positive rated power is refused with -1, because dividing by it is
    undefined.
  - A non-positive mass is refused with -1, because the rotor term would
    vanish and the result would silently mean a different aircraft.
  - A non-positive rotor disc area is refused with -1, because the hover
    denominator is then undefined.
  - The returned fraction is clamped to 0..1.
  - The fraction is floored at the declared idle fraction, so a parked or
    idling aircraft shows a small plume rather than none.

Arguments:
  0:  _massKg         (NUMBER) aircraft mass, kg, > 0
  1:  _speedMS        (NUMBER) true airspeed, m/s, made a magnitude
  2:  _class          (STRING) aircraft class, selects the wing or rotor term
  3:  _ratedPowerW    (NUMBER) rated engine power, W, > 0
  4:  _dragAreaM2     (NUMBER) effective drag area Cd*S, m^2
  5:  _rotorDiscAreaM2 (NUMBER) rotor disc area, m^2, > 0
  6:  _idleFraction   (NUMBER) declared idle load floor, 0..1
  7:  _airDensity     (NUMBER) air density, kg/m^3

Return Value: NUMBER, the load fraction in 0..1, or -1 when an input is
unusable.
Example: [1100, 58, "B_Plane_CAS_01_F", 134000, 0.688, 50, 0.05, AERO_ISA_SEA_LEVEL_DENSITY] call aee_flight_fnc_calculateAirEngineLoad
Public: No
*/

params [
    ["_massKg", 0, [0]],
    ["_speedMS", 0, [0]],
    ["_class", "", [""]],
    ["_ratedPowerW", 150000, [0]],
    ["_dragAreaM2", 0.7, [0]],
    ["_rotorDiscAreaM2", 50, [0]],
    ["_idleFraction", 0.05, [0]],
    ["_airDensity", AERO_ISA_SEA_LEVEL_DENSITY, [0]]
];

// A non-positive rated power cannot be divided by, a non-positive mass removes
// the rotor term so the result would mean a different aircraft, and a
// non-positive disc area makes the hover denominator undefined.
if (_ratedPowerW <= 0) exitWith { -1 };
if (_massKg <= 0) exitWith { -1 };
if (_rotorDiscAreaM2 <= 0) exitWith { -1 };

private _speed = abs _speedMS;
private _rho = _airDensity max 0;

// A helicopter is the only air root with a rotor.  Any other air class is a
// wing, so a third air root cannot fall through to the idle.
private _rotor = false;
if (_class isEqualType "") then {
    if (_class != "") then { _rotor = _class isKindOf "Helicopter"; };
};

private _load = 0;
if (_rotor) then {
    // Momentum theory: the ideal induced hover power, W^1.5 / sqrt (2 rho A).
    private _weightN = _massKg * STANDARD_GRAVITY;
    private _hoverW = (_weightN ^ 1.5) / sqrt (2 * _rho * _rotorDiscAreaM2);
    _load = _hoverW / _ratedPowerW;
} else {
    // Steady level flight: the drag power 0.5 rho (Cd S) v^3.
    private _dragW = 0.5 * _rho * _dragAreaM2 * _speed * _speed * _speed;
    _load = _dragW / _ratedPowerW;
};

// The idle floor is the declared minimum while the engine runs.
private _idle = _idleFraction max 0 min 1;
_load = (_load max _idle) min 1;

_load
