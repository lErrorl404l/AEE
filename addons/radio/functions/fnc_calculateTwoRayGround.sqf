#include "..\script_component.hpp"

/*
Two-ray ground-reflection excess path loss (issue #13).

The direct ray and the ground-reflected ray interfere.  The received field is
    E = E0 * (1 + Gamma * exp(-j * deltaPhi))
with the reflection coefficient Gamma (the real magnitude -rho, the sign
folded into the phase) and the phase difference between the two rays
    deltaPhi = 2*pi*deltaR/lambda,   deltaR = 2*hTx*hRx/d
so
    deltaPhi = 4*pi*hTx*hRx/(lambda*d).

The power relative to free space is the interference factor
    F = |1 + Gamma*exp(-j*deltaPhi)|^2 = 1 + rho^2 - 2*rho*cos(deltaPhi)
and the excess path loss over free space is  L = -10*log10(F) dB.

Two regimes fall out of the SAME expression:

  * rho = 1 (perfect, smooth ground): F = 4*sin^2(deltaPhi/2).  Below the
    breakpoint  d_bp = 4*hTx*hRx/lambda  the two rays interfere in lobes
    (constructive where deltaPhi = pi, F = 4, L = -6 dB; destructive nulls
    where F tends to 0).  Beyond d_bp the envelope falls as d^-4:
    40*log10(d).
  * rho < 1 (rough real ground): the reflected ray is weaker, the nulls are
    shallow and the excess saturates at -10*log10((1-rho)^2).

SOURCE: two-ray ground-reflection model (Balanis, "Antenna Theory", 4th ed
2016; Freeman, "Radio System Design for Telecommunications", 2007).  The
breakpoint and the d^4 far-field form are standard.  The interference
identity |1 - exp(-j*phi)| = 2*|sin(phi/2)| and the derivation are given at
https://en.wikipedia.org/wiki/Two-ray_ground-reflection_model

UNSOURCED (recorded, not derived): the reflectivity passed by the caller is a
rough-ground effective value; the roughness reduction of the Fresnel
coefficient is not computed here.  The interference factor is floored at
1e-12 so the logarithm stays finite at an exact null; the floor is a
numerical guard, not a modelled null depth.

Args:
  0: distance     <NUMBER> link range, m
  1: frequency    <NUMBER> carrier, Hz
  2: tx height    <NUMBER> transmitter above ground, m
  3: rx height    <NUMBER> receiver above ground, m
  4: reflectivity <NUMBER> 0..1 effective reflection magnitude

Return: <ARRAY> [excessLossDB, breakpointM]
  excessLossDB is the loss ADDED to the free-space path loss (negative where
  the two rays add constructively).
*/

params [
    ["_distM", 5000, [0]],
    ["_freqHz", 1e8, [0]],
    ["_hTx", 2, [0]],
    ["_hRx", 1.5, [0]],
    ["_reflectivity", 0.5, [0]]
];

private _lambda = 3e8 / (_freqHz max 1);
private _d = _distM max 1;
private _hT = _hTx max 0.1;
private _hR = _hRx max 0.1;
private _rho = (_reflectivity max 0) min 1;

// Breakpoint: the distance at which deltaPhi = pi (the first lobe peak).
private _breakpoint = (4 * _hT * _hR) / _lambda;

// Phase difference in DEGREES (SQF cos takes degrees).
private _deltaPhi = ((4 * pi * _hT * _hR) / (_lambda * _d)) * 180 / pi;

// Interference factor, floored at 1e-12 so the log stays finite at a null.
private _field = ((1 + (_rho ^ 2)) - (2 * _rho * (cos _deltaPhi))) max 1e-12;

private _excess = -10 * (log _field);

[_excess, _breakpoint]
