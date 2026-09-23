#include "..\script_component.hpp"

/*
Terrain and geometry limits for a ground vehicle (issue #117).

Three independent limits decide whether a vehicle can cross a piece of
terrain.  All are geometry, not soil, so they are separate from the NRMM
soil-strength test in fnc_calculateSoilStrength.

  Breakover angle.  The crest angle a vehicle clears without the chassis
  underside touching the apex:
      tan(beta / 2) = 2 c / L,  so  beta = 2 atan(2 c / L)
    c is ground clearance, L the wheelbase.  The derivation: with the
    vehicle straddling a crest, the clearance to the apex is
    (L/2) tan(theta) - c, which is zero at the limit.  Source: SAE J1100
    and J689 definitions; AM General M1151 datasheet for the measured
    value.  The formula ignores tyre deflection, so a manufacturer's
    measured breakover is more authoritative than the formula for that
    vehicle; both are returned.

  Gradeability.  The steepest slope a vehicle can climb at steady state.
  The exact road-load balance, with rolling resistance f_r and tractive
  force F on weight W:
      theta = asin( (F/W) / sqrt(1 + f_r^2) ) - atan(f_r)
    Source: Gillespie, Fundamentals of Vehicle Dynamics (SAE 1992),
    road-load equation.  The common small-angle form
    tan(theta) = (F - R)/W is the approximation and is NOT used.

  Friction limit.  On a low-friction surface the tyres slip before the
  engine runs out of force.  With all wheels driven:
      tan(theta) <= mu - f_r
    Source: Gillespie road-load with F_max = mu W cos(theta).

  Side-slope limit.  A vehicle tips when the lateral acceleration reaches
  its Static Stability Factor (NHTSA):
      tan(theta_tip) = SSF = T / (2 h)
    The operational limit is usually lower: manufacturers publish a
    maximum side slope well below the tip angle.  Both are returned and
    the LOWER governs.  The SSF itself comes from fnc_calculateSSF (#108),
    so the rollover and side-slope limits share one model.

  Fording.  A vehicle may ford to its published depth.  The engine exposes
  no ford depth, so a class table carries it; water deeper than the ford
  depth stops the vehicle, and the published fording speed cap applies.
  Source: TM 9-2320-387-10 (HMMWV: 30 in / 0.76 m shallow, 60 in / 1.52 m
  with the deep-water kit, 5 mph / 8 kph cap).

Arguments:
  0: vehicle (OBJECT)
  1: slopeDeg (NUMBER) - the terrain slope in the direction of travel

Return Value: ARRAY [breakoverDeg, gradeDeg, sideSlopeDeg, canCross, fordDepthM]
Example: [cursorObject, 15] call aee_mobility_fnc_calculateTerrainLimits
Public: No
*/

params [
    ["_vehicle", objNull, [objNull]],
    ["_slopeDeg", 0, [0]]
];

if (isNull _vehicle) exitWith { [0, 0, 0, false, 0] };

// ─── Geometry by class ───────────────────────────────────────────────────
// clearance in metres, wheelbase in metres, ford depth in metres, and the
// published maximum side slope in degrees.  Sources: the operator manual of
// the vehicle each class represents.
private _spec = [0.40, 3.20, 0.76, 30];   // default: a light 4x4 / HMMWV
{
    if (_vehicle isKindOf (_x select 0)) exitWith {
        _spec = _x select 1;
    };
} forEach [
    ["MRAP",        [0.66, 3.90, 0.99, 30]],   // Cougar: 0.99 m ford
    ["Wheeled_APC", [0.50, 4.20, 1.00, 25]],
    ["Tank",        [0.47, 4.60, 1.20, 20]],   // M1: 1.2 m, 2.0 m with DWFK
    ["Tracked_APC", [0.45, 4.00, 1.00, 25]],
    ["Car",         [0.20, 2.60, 0.40, 30]],
    ["Truck",       [0.40, 4.00, 0.90, 25]]
];

_spec params ["_clearance", "_wheelbase", "_fordDepth", "_sideLimit"];

// The vehicle's own geometry overrides the class estimate where it is
// readable (fnc_getVehicleGeometry): a measured wheelbase is real data, and
// the breakover angle depends on it directly.  Clearance has no engine
// source, so it stays on the class table.
private _geo = [_vehicle] call FUNC(getVehicleGeometry);
if ((_geo select 1) > 0) then { _wheelbase = _geo select 1; };

// ─── Breakover ───────────────────────────────────────────────────────────
private _breakover = 2 * (atan ((2 * _clearance) / _wheelbase)) * 57.2957795;

// ─── Gradeability ────────────────────────────────────────────────────────
// Tractive force over weight, from the traction model's coefficient (the
// mu the slip curve produces), and a rolling-resistance coefficient of
// 0.015 on a hard surface, which is the published road value.
private _mu = missionNamespace getVariable [QGVAR(muSurface), 0.85];
if !(_mu isEqualType 0) then { _mu = 0.85; };
private _fr = 0.015;

// The force available is mu * W (all wheels driven); the resistance is
// fr * W.  In the (F/W) term the weight cancels, leaving mu.
private _fw = _mu;
private _tanTerm = _fw / (sqrt (1 + _fr * _fr));
private _gradeRad = asin ((_tanTerm min 1) max -1) - atan _fr;
private _grade = _gradeRad * 57.2957795;

// Friction limit: below this the tyres slip first.
private _frictionLimit = (atan (_mu - _fr)) * 57.2957795;

// The usable grade is the lower of the two.
private _gradeUsable = _grade min _frictionLimit;
if (_gradeUsable < 0) then { _gradeUsable = 0; };

// ─── Side slope ──────────────────────────────────────────────────────────
private _ssfArr = [_vehicle] call FUNC(calculateSSF);
private _ssf = _ssfArr select 0;
private _tipDeg = if (_ssf > 0) then {
    (atan _ssf) * 57.2957795
} else {
    0
};

// The published operational limit governs when it is lower than the tip.
private _sideSlope = [_sideLimit, _tipDeg]
    select ((_tipDeg > 0) && (_tipDeg < _sideLimit));

// ─── Can the vehicle cross the given slope? ─────────────────────────────
// It must be within the grade limit AND not exceed the side-slope limit.
private _canCross = (_slopeDeg <= _gradeUsable) && (_slopeDeg <= _sideSlope);

missionNamespace setVariable [QGVAR(currentBreakoverDeg), _breakover];
missionNamespace setVariable [QGVAR(currentGradeLimitDeg), _gradeUsable];
missionNamespace setVariable [QGVAR(currentSideSlopeLimitDeg), _sideSlope];

[_breakover, _gradeUsable, _sideSlope, _canCross, _fordDepth]
