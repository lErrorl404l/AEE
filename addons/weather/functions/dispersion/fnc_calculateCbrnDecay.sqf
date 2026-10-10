#include "..\..\script_component.hpp"

/*
CBRN agent atmospheric decay from its half-life.

Source: first-order decay C(t) = C0 exp(-t/tau), with the time constant
tau = t_half / ln 2.  The per-agent half-lives are the FM 3-11 persistence
figures (see fnc_getCbrnAgent).  This is the intrinsic atmospheric decay;
the environmental (temperature/humidity) scaling of surface contamination
is owned by the existing Arrhenius model, fnc_calculateCBRNPersistence.

Arguments:
  0: initial concentration C0 (NUMBER, mg/m3)
  1: elapsed time t (NUMBER, hours)
  2: half-life t_half (NUMBER, hours)

Returns the decayed concentration (mg/m3).
*/

params [
    ["_c0", 0, [0]],
    ["_elapsedH", 0, [0]],
    ["_halfLifeH", 1, [0]]
];

private _tau = (_halfLifeH / ln 2) max 0.0001;

_c0 * exp (-(_elapsedH / _tau))
