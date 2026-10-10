#include "..\..\script_component.hpp"

/*
First-order lag on the pupil diameter.

The pupil constricts faster than it redilates. For a step of equal size the
constriction is the quicker branch, so the time constant is chosen from the
sign of the error.

TRACED: constriction tau 0.25 s, redilation 1.9x (Meethal 2021,
Sci Rep 11:21090). The 1.9 ratio gives the default dilate tau 0.475 s.

Arguments:
  0: Number - current diameter, mm
  1: Number - steady target diameter, mm
  2: Number - time step, s
  3: Number - constriction time constant, s
  4: Number - redilation time constant, s

Returns:
  Number - lagged diameter after this step, mm.
*/

params [
    ["_d", 0, [0]],
    ["_dTarget", 0, [0]],
    ["_dt", 0, [0]],
    ["_tauConstrict", 0.25, [0]],
    ["_tauDilate", 0.475, [0]]
];

private _tau = _tauDilate;
if (_dTarget < _d) then { _tau = _tauConstrict; };

_d + ((_dTarget - _d) * (1 - (exp (- (_dt / _tau)))))
