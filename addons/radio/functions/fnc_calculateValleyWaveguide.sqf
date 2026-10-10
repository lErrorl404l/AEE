#include "..\script_component.hpp"

/*
Valley waveguide effect (issue #13).

A valley walls the radio wave the way a parallel-plate guide does.  The
cutoff frequency of a parallel-plate guide of width a is
    f_c = c / (2*a)
and the guided wavelength is
    lambda_g = lambda / sqrt(1 - (f_c/f)^2)
Below cutoff the valley does not guide the wave at all.

SOURCE (cutoff and guided wavelength): parallel-plate / rectangular-waveguide
TE10 result, Pozar "Microwave Engineering" (standard waveguide theory).  The
exact section was not pinned this session; treat the cutoff form as standard.

UNSOURCED: the coupling magnitudes.  No standardised valley-waveguide radio
propagation model was found (Crossref/Semantic Scholar return only tunnel,
sea-surface duct and Earth-ionosphere waveguide work; ITU-R P.526 does not
cover valley channelling).  The along-axis bonus and across-axis penalty
below are a FIRST-ORDER GEOMETRIC ANALOGY, not a published model.  Their
magnitudes (3 dB along, 1.5 dB across) are UNSOURCED and are recorded as
such.  The angle is the bearing of the link relative to the valley axis.

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

// Coupling rises from 0 at cutoff toward 1 well above it.
private _coupling = sqrt (1 - ((_fCutoff / _freqHz) ^ 2));

// Along-axis bonus, across-axis penalty.  Magnitudes UNSOURCED (see header).
private _alongBonus = 3 * _coupling * ((cos _angleDeg) ^ 2);
private _acrossPenalty = 1.5 * _coupling * ((sin _angleDeg) ^ 2);

(_acrossPenalty - _alongBonus)
