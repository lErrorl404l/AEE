#include "..\script_component.hpp"

/*
Fixed-wing performance row from the density ratio (issue #22).

Given the density ratio and a few airframe inputs, this returns the derived
performance quantities the minimal model needs:

  TAS       = IAS / sqrt(sigma)              (true versus indicated)
  V_stall   = V_stall0 / sqrt(sigma)         (lift = 0.5 rho V^2 S CL)
  power     = engine power or thrust ratio   (FUNC(calculatePowerRatio))
  ground    = induced-drag reduction         (FUNC(calculateGroundEffect))
  takeoff   = ground-roll multiplier, 1/(sigma * power)
  landing   = ground-roll multiplier, 1/sigma

The takeoff multiplier follows the takeoff ground-roll relation
S_g = 1.21 W^2 / (g rho S CL_max (T - D)).  With W, S and CL_max fixed the
roll scales as 1/(rho T), that is 1/(sigma * power).  It reproduces the issue's
jet anchor (1.61 at 8000 ft) and piston anchor (1.6 to 1.7).  The landing roll
S_L = 1.69 W / (g rho S CL_max mu) scales as 1/rho = 1/sigma (1.27 at 8000 ft).
A headwind shortens the roll by 1 percent per knot and a tailwind lengthens it
by 5 percent per knot.

Source: FAA Airplane Flying Handbook; the takeoff and landing ground-roll
relations (issue #22, from the flight-mechanics references).  The wind
corrections are the FAA rule of thumb.

This is a pure kernel; it reads no engine state.

Arguments:
  0: NUMBER - density ratio sigma = rho / 1.225
  1: NUMBER - indicated airspeed, knots
  2: NUMBER - sea-level stall speed, knots
  3: STRING - propulsion token: piston_prop, turbojet, turbofan or turboprop
  4: NUMBER - height above ground, metres
  5: NUMBER - wingspan, metres
  6: NUMBER - headwind component, knots (negative for a tailwind)

Return Value: ARRAY - [tasKt, stallKt, powerRatio, groundEffect,
                       takeoffMultiplier, landingMultiplier]
Example: [0.789, 100, 100, "piston_prop", 5, 10, 0] call aee_flight_fnc_calculateFixedWingPerformance
Public: No
*/

params [
    ["_sigma", 1, [0]],
    ["_iasKt", 0, [0]],
    ["_stallKt", 0, [0]],
    ["_propulsion", "", [""]],
    ["_heightAglM", 0, [0]],
    ["_wingspanM", 0, [0]],
    ["_headwindKt", 0, [0]]
];

private _safeSigma = _sigma max 0.01;
private _speedRatio = 1 / (sqrt _safeSigma);

private _tasKt = _iasKt * _speedRatio;
private _stallScaledKt = _stallKt * _speedRatio;
private _powerRatio = [_safeSigma, _propulsion] call FUNC(calculatePowerRatio);
private _groundEffect = [_heightAglM, _wingspanM] call FUNC(calculateGroundEffect);

// A headwind is a positive component and shortens the roll.  A tailwind is a
// negative component and lengthens it.
private _windFactor = 1 - 0.01 * (_headwindKt max 0) + 0.05 * ((0 - _headwindKt) max 0);

private _takeoffMultiplier = _windFactor / (_safeSigma * _powerRatio);
private _landingMultiplier = _windFactor / _safeSigma;

[_tasKt, _stallScaledKt, _powerRatio, _groundEffect, _takeoffMultiplier, _landingMultiplier]
