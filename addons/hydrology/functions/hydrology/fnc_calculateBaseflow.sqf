#include "..\..\script_component.hpp"
/*
Baseflow recession, the linear reservoir (issue #24).

After the rain stops, a catchment keeps draining. The slow store is
groundwater, and the standard model is a linear reservoir whose outflow
is proportional to the water it holds:

  Q_g = k_g * S_g
  Q(t) = Q0 * exp(-k_g * t)
  K    = exp(-k_g * dt)          the daily recession constant

A baseflow index of 0.9 to 0.99 per day is typical for a perennial
stream, which is what makes a river carry water in a dry week.

Source: USGS SIR 2022-5114 (baseflow separation and recession); the
linear-reservoir form is the standard baseflow filter.

Args:
  0: current store (NUMBER, mm, default 0)
  1: inflow to the store (NUMBER, mm, default 0)
  2: recession rate k_g (NUMBER, per day, default 0.2)
  3: interval (NUMBER, seconds, default 5)

Returns [newStore_mm, baseflowOut_mm].
*/

params [
    ["_store", 0, [0]],
    ["_inflow", 0, [0]],
    ["_kG", 0.2, [0]],
    ["_interval", 5, [0]]
];

if !(_store isEqualType 0) then { _store = 0; };
if !(_inflow isEqualType 0) then { _inflow = 0; };
if !(_kG isEqualType 0) then { _kG = 0.2; };
if !(_interval isEqualType 0) then { _interval = 5; };
_store = _store max 0;

// The step is a fraction of a day, so the decay is exp(-k_g * dt_days).
private _dtDays = _interval / 86400;
private _decay = exp (-_kG * _dtDays);
private _newStore = (_store + _inflow) * _decay;

// Outflow is what left the store over the step.
private _outflow = (_store + _inflow) - _newStore;

[_newStore max 0, _outflow max 0]
