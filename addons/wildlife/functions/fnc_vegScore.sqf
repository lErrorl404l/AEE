#include "..\script_component.hpp"

/*
Vegetation score kernel (wildlife ecology).

The single reader of the published terrain signals.  Element 1 is a HashMap
of Koppen code to indicator vote weight, published by fnc_scanTerrainSignals
(line 202).  The strongest single vote is the score, clamped 0 to 1.  Max
rather than sum: one tree votes for several Koppen codes, so a sum
double-counts one species.  A legacy numeric element is accepted and clamped,
so every reader shares one shape and the old element-1 divergence cannot
return.

The wildlife tick, the spawn path and the animal vegetation provider all call
this kernel.

Arguments:
  0: Array - the terrain signals [surfaceVotes, vegVotes, ...]

Returns:
  Number - the vegetation score, 0 to 1
*/

params [["_signals", [], [[]]]];

if ((count _signals) < 2) exitWith { 0 };

private _votes = _signals select 1;

// A legacy numeric signal is clamped and returned.
if (_votes isEqualType 0) exitWith { ((_votes max 0) min 1); };

// The HashMap shape: the strongest single vote.
private _list = values _votes;
private _score = 0;
for "_i" from 0 to ((count _list) - 1) do {
    private _vote = _list select _i;
    if (_vote > _score) then { _score = _vote; };
};

((_score max 0) min 1)
