#include "..\script_component.hpp"

/*
Deterministic pseudo-random value in [0, 1) from two integer seeds.

A linear congruential generator. Mission time and position are identical
on every machine, so the same seeds produce the same value everywhere.
Event rolls (lightning, microburst, space weather) use this so all
clients agree on event state; the seed includes a time component so the
value changes between ticks.

Arguments:
  0: seed 1 (Number, e.g. round (time * 10))
  1: seed 2 (Number, event-specific salt)

Return Value:
  Number 0..1
*/

params ["_seed1", "_seed2"];
private _s = ((_seed1 * 1000003) + _seed2) % 2147483648;
(((_s * 1103515245) + 12345) % 2147483648) / 2147483648
