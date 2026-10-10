#include "..\script_component.hpp"

/*
Monostatic radar detection range (pure).

    R_max = ( Pt * G^2 * lambda^2 * sigma / ( (4*pi)^3 * Pmin ) ) ^ (1/4)

    Pt     peak transmit power, W
    G      antenna gain (linear), transmit and receive the same
    lambda wavelength, m
    sigma  target radar cross section, m2
    Pmin   minimum detectable power, W (fnc_calculateRadarNoiseFloor)

The fourth root is the two-way (R^4) law: doubling the range costs 16x the
power (12 dB), and the range scales as sigma^(1/4).  A 100x RCS increase
therefore multiplies the range by 100^(1/4) = 3.162, which is the issue's
"100x RCS = 3.2x range".  This is a DIFFERENT law from the radio link budget
(fnc_calculateRadioPropagation), which is one-way (R^2); the two must not be
confused, and this kernel does not reuse the Friis form.

SOURCE.  Skolnik, "Radar Handbook", 3rd ed., McGraw-Hill, 2008, ISBN
978-0-07-148547-0, ch. 1 (the radar range equation); MIT Lincoln Laboratory,
"Introduction to Radar Systems" (web course), Lecture 4 "Target RCS" (the RCS
material; the range equation itself is Skolnik's).

CANONICAL OWNER.  The radar range equation is defined once, in
addons/radio/functions/radar/fnc_radarRangeEquation.sqf (issue #104).  This
seeker-facing entry point delegates to it, so the repository keeps one model
of the physics and the missile-seeker call site stays unchanged.

Arguments:
  0: _peakPowerW         (NUMBER) Pt, W, > 0
  1: _gain               (NUMBER) G, linear, > 0
  2: _wavelengthM        (NUMBER) lambda, m, > 0
  3: _rcsM2              (NUMBER) sigma, m2, > 0
  4: _minDetectablePowerW (NUMBER) Pmin, W, > 0

Return Value: NUMBER - maximum detection range in metres.  Returns 0 when any
argument is not positive.
Public: No
*/

params [
    ["_peakPowerW", 0, [0]],
    ["_gain", 0, [0]],
    ["_wavelengthM", 0, [0]],
    ["_rcsM2", 0, [0]],
    ["_minDetectablePowerW", 0, [0]]
];

if (_peakPowerW <= 0) exitWith { 0 };
if (_gain <= 0) exitWith { 0 };
if (_wavelengthM <= 0) exitWith { 0 };
if (_rcsM2 <= 0) exitWith { 0 };
if (_minDetectablePowerW <= 0) exitWith { 0 };

[_peakPowerW, _gain, _wavelengthM, _rcsM2, _minDetectablePowerW] call FUNC(radarRangeEquation)
