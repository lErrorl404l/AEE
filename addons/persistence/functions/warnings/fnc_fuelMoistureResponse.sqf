#include "..\..\script_component.hpp"

/*
Timelag response of a dead fuel class toward its equilibrium moisture.

A dead fuel particle changes moisture exponentially toward the EMC with a
time constant (timelag) set by its diameter.  The Rothermel fuel classes are
the 1-hour (diameter < 6 mm), 10-hour (6 to 25.4 mm) and 100-hour
(25.4 to 76.2 mm) size classes; a smaller particle tracks the EMC faster.

  M(t+dt) = EMC + (M(t) - EMC) * exp(-dt / tau)

Source: Rothermel (1972) INT-115; timelag classes per Fosberg (1977) and the
NWCG fuel-moisture model.  tau is the class timelag in hours (1, 10, 100).

Params:
  _mPrev   previous class moisture, fraction
  _emc     equilibrium moisture for the class, fraction
  _dtS     elapsed time, seconds
  _tauH    timelag of the class, hours

Returns the new class moisture as a fraction.
*/

params [
    ["_mPrev", 0.08, [0]],
    ["_emc", 0.08, [0]],
    ["_dtS", 5, [0]],
    ["_tauH", 1, [0]]
];

private _tau = _tauH max 0.001;
private _decay = (_dtS / 3600) / _tau;

_emc + (_mPrev - _emc) * exp (-_decay)
