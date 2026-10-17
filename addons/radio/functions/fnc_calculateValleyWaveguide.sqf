#include "..\script_component.hpp"

/*
Valley waveguide effect (issue #13).

A valley walls the radio wave the way a parallel-plate guide does.  The
cutoff frequency of a parallel-plate guide of width a is
    f_c = c / (2*a)
and the guided wavelength is
    lambda_g = lambda / sqrt(1 - (f_c/f)^2)
Below cutoff the valley does not guide the wave at all.

SOURCE (cutoff and guided wavelength): standard rectangular-waveguide /
parallel-plate result, D. M. Pozar, "Microwave Engineering", 4th ed., Wiley,
2012, section 3.3 (parallel-plate guide cutoff f_c = c/(2a)) and section 3.4
(guided wavelength).  The coupling factor below is the reciprocal ratio
lambda / lambda_g = sqrt(1 - (f_c/f)^2) from the same result, so it is
derived, not tuned.

GAME TUNABLES: the two dB magnitudes.  No standard model covers terrain-valley
channelling.  A source check confirmed ITU-R P.526-16 ("Propagation by
diffraction") has no valley or ducting section, and ITU-R P.2001-6 models
ducting statistically (sub-model 2, Attachment D) with no guidance bonus for a
terrain valley.  The closest published model is ITU-R P.1411-13 section 4.1
(propagation within street canyons, a building channel), but it is a
site-general path-loss model of the form Lb = 10 a log10(d) + b + 10 g log10(f)
that needs the link distance, which this kernel does not take, so it cannot be
applied as a distance-free dB modifier.  The along-axis bonus and across-axis
penalty below are therefore a FIRST-ORDER GEOMETRIC ANALOGY with GAME TUNABLE
magnitudes (3 dB along, 1.5 dB across), not a published model.  The angle is
the bearing of the link relative to the valley axis.

Args:
  0: width     <NUMBER> valley width, m
  1: frequency <NUMBER> carrier, Hz
  2: angle     <NUMBER> link bearing relative to the valley axis, degrees

Return: <NUMBER> path-loss modifier, dB (negative = guidance bonus along the
  axis, positive = penalty across it, 0 = no guidance).
*/

params [
    ["_widthM", 0, [0]],
    ["_freqHz", 1e8, [0]],
    ["_angleDeg", 0, [0]]
];

if (_widthM <= 0) exitWith { 0 };

// Parallel-plate cutoff: f_c = c / (2a).
private _fCutoff = 3e8 / (2 * _widthM);

// Below cutoff the valley does not guide the wave: no effect.
if (_freqHz <= _fCutoff) exitWith { 0 };

// Coupling is the guided-wavelength ratio lambda / lambda_g = sqrt(1 - (f_c/f)^2):
// 0 at cutoff, approaching 1 well above it.  This part is derived (Pozar 3.4).
private _coupling = sqrt (1 - ((_fCutoff / _freqHz) ^ 2));

// Along-axis bonus, across-axis penalty.  The magnitudes are GAME TUNABLES
// (see header): no published valley-waveguide dB model exists.
private _alongBonusMax = 3;
private _acrossPenaltyMax = 1.5;
private _alongBonus = _alongBonusMax * _coupling * ((cos _angleDeg) ^ 2);
private _acrossPenalty = _acrossPenaltyMax * _coupling * ((sin _angleDeg) ^ 2);

(_acrossPenalty - _alongBonus)
